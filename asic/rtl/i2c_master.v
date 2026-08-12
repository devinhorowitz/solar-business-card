// ---------------------------------------------------------------------------
// i2c_master.v -- DRH-1 companion ASIC: single-transaction I2C bus master.
//
// Mirrors firmware/twi.h, the card's minimal blocking TWI0 host -- specifically
// the two entry points its callers (adxl367.c / nfc.c / fram.c) actually use:
//   twi_reg_write(addr7, reg, val)      -> START, addr+W, reg, data, STOP
//   twi_reg_read (addr7, reg, dst, 1)   -> START, addr+W, reg, reSTART,
//                                          addr+R, byte, NACK, STOP
// as required by SPEC.md. Single-byte reads only, NACK-last (the ADXL367
// auto-increments natively; twi.h's bit7 burst convention and the NT3H
// last-byte-ACK quirk are deliberately not carried over -- init_seq only ever
// does single-register accesses, same as the accel driver on the card).
// Like twi.h's return convention, any NACK (address or data) aborts the
// transaction with a clean STOP and reports a fault (ack_err) -- the caller
// treats it as "device not talking" and skips gracefully.
//
// Timing: SCL period = 4*DIV clk cycles (DIV clk per quarter-phase), so with
// the nominal 1 MHz on-die RC and DIV=5, SCL ~= 50 kHz. SDA changes on entry
// to the first low quarter; SCL is high for quarters 1-2; the master samples
// SDA mid-high (entry to quarter 2).
//
// SPEC.md contract (do not deviate): Verilog-2001, one clock, synchronous
// rst_n, no latches, no initial blocks, done is a 1-cycle strobe, SDA is the
// only tri-state:  assign sda = sda_oe ? 1'b0 : 1'bz;  -- sampled via the pin.
//
// HARDENING RULE (pad-level tri-state only): the `assign sda = ...` below is
// the ONE permitted tri-state, and it models the pad driver, nothing more.
// Core logic never reads a Z or drives the resolved net directly -- it reads
// the pin level (sda_in, i.e. the inout sampled as an input) and drives via
// the sda_oe enable, which is also exported as the sda_oe_o port so a wrapper
// or padframe can build its own open-drain driver from {oe, 0}. If this
// module ever goes through a flow that rejects boundary tri-states (yosys
// tolerates this one with a warning in the drh1_top size-gate flow), delete
// the assign, turn `inout sda` into `input sda_in`, and drive the pad from
// sda_oe_o outside -- no internal logic changes are needed.
// ---------------------------------------------------------------------------

module i2c_master #(parameter DIV = 5) (   // SCL ~= clk / (4*DIV) ~= 50 kHz
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire [6:0] dev_addr,
    input  wire       rw,                  // 0 = write
    input  wire [7:0] reg_addr,
    input  wire [7:0] wdata,
    output reg  [7:0] rdata,
    output reg        busy,
    output reg        done,                // 1-cycle strobe
    output reg        ack_err,
    inout  wire       sda,
    output wire       sda_oe_o,            // mirror of the internal sda_oe (pad oe)
    output reg        scl
);

    // SDA open-drain: drive low or release; never drive high (twi.h's rule).
    reg sda_oe;                            // 1 = drive SDA low
    assign sda = sda_oe ? 1'b0 : 1'bz;     // sample via the pin (TB pullup)
    assign sda_oe_o = sda_oe;              // exported for wrapper/padframe use

    // Bit-engine states
    localparam [2:0] S_IDLE  = 3'd0,       // bus released, SCL high
                     S_START = 3'd1,       // START / repeated START
                     S_TX    = 3'd2,       // shift one byte out, MSB first
                     S_ACK   = 3'd3,       // slave ACK slot (SDA released)
                     S_RX    = 3'd4,       // shift one byte in, MSB first
                     S_MACK  = 3'd5,       // master NACK slot (SDA released)
                     S_STOP  = 3'd6;       // STOP, then done

    // Which byte of the transaction we are on
    localparam [2:0] G_ADDRW = 3'd0,       // dev_addr + W
                     G_REG   = 3'd1,       // register sub-address
                     G_WDATA = 3'd2,       // write data (write txn)
                     G_ADDRR = 3'd3,       // dev_addr + R (after reSTART)
                     G_RDATA = 3'd4;       // read data byte

    reg [2:0]  state;
    reg [2:0]  stage;
    reg [1:0]  phase;                      // quarter-phase within a symbol
    reg [15:0] cnt;                        // quarter-phase prescaler
    reg [7:0]  shreg;
    reg [2:0]  bit_cnt;
    reg        nack;                       // sampled ACK bit (1 = NACK)
    reg [6:0]  a_lat;                      // inputs latched at start
    reg        rw_lat;
    reg [7:0]  r_lat, w_lat;

    wire q_tick = (cnt == DIV - 1);        // one quarter-phase elapsed

    // Byte sent right after a (repeated) START
    wire [7:0] tx_byte = (stage == G_ADDRR) ? {a_lat, 1'b1} : {a_lat, 1'b0};

    // Quarter-phase convention (each phase lasts DIV clk):
    //   entry to phase 0: SCL low,  SDA set/changed
    //   entry to phase 1: SCL high
    //   entry to phase 2: sample point (SCL mid-high)
    //   entry to phase 3: SCL low
    // The case(phase) below fires at the END of the named phase, i.e. it
    // performs the ENTRY actions of the next phase.  All SCL rising edges of
    // a transaction are therefore exactly 4*DIV clk apart.
    always @(posedge clk) begin
        if (!rst_n) begin
            state   <= S_IDLE;
            stage   <= G_ADDRW;
            phase   <= 2'd0;
            cnt     <= 16'd0;
            shreg   <= 8'd0;
            bit_cnt <= 3'd0;
            nack    <= 1'b0;
            a_lat   <= 7'd0;
            rw_lat  <= 1'b0;
            r_lat   <= 8'd0;
            w_lat   <= 8'd0;
            rdata   <= 8'd0;
            busy    <= 1'b0;
            done    <= 1'b0;
            ack_err <= 1'b0;
            scl     <= 1'b1;
            sda_oe  <= 1'b0;
        end else begin
            done <= 1'b0;                          // 1-cycle strobe

            if (state == S_IDLE) begin
                scl    <= 1'b1;
                sda_oe <= 1'b0;
                cnt    <= 16'd0;
                phase  <= 2'd0;
                if (start) begin
                    busy    <= 1'b1;
                    ack_err <= 1'b0;
                    nack    <= 1'b0;
                    a_lat   <= dev_addr;
                    rw_lat  <= rw;
                    r_lat   <= reg_addr;
                    w_lat   <= wdata;
                    stage   <= G_ADDRW;
                    state   <= S_START;
                    scl     <= 1'b0;               // S_START phase 0: SCL low,
                    sda_oe  <= 1'b0;               // SDA released (idle high)
                end
            end else if (!q_tick) begin
                cnt <= cnt + 16'd1;
            end else begin
                cnt   <= 16'd0;
                phase <= phase + 2'd1;             // 3 wraps to 0

                case (state)

                    // START / repeated START: SDA falls while SCL is high.
                    // (From a mid-transaction low-SCL point, phase 0 first
                    // releases SDA under the low clock -- legal data move.)
                    S_START: case (phase)
                        2'd0: scl    <= 1'b1;
                        2'd1: sda_oe <= 1'b1;      // SDA low @ SCL high: START
                        2'd2: scl    <= 1'b0;
                        2'd3: begin                // -> first bit of tx_byte
                            shreg   <= tx_byte;
                            bit_cnt <= 3'd0;
                            sda_oe  <= ~tx_byte[7];
                            state   <= S_TX;
                        end
                    endcase

                    // Transmit one byte, MSB first
                    S_TX: case (phase)
                        2'd0: scl <= 1'b1;
                        2'd1: ;                    // data stable through high
                        2'd2: scl <= 1'b0;
                        2'd3: begin
                            if (bit_cnt == 3'd7) begin
                                sda_oe <= 1'b0;    // release for slave ACK
                                state  <= S_ACK;
                            end else begin
                                bit_cnt <= bit_cnt + 3'd1;
                                shreg   <= {shreg[6:0], 1'b0};
                                sda_oe  <= ~shreg[6];
                            end
                        end
                    endcase

                    // Slave ACK slot: sample mid-high, decide at phase end
                    S_ACK: case (phase)
                        2'd0: scl  <= 1'b1;
                        2'd1: nack <= sda;         // 1 = no ACK (pullup)
                        2'd2: scl  <= 1'b0;
                        2'd3: begin
                            if (nack) begin
                                ack_err <= 1'b1;   // NACK: abort with STOP
                                sda_oe  <= 1'b1;   // STOP phase 0: SDA low
                                state   <= S_STOP; //   under the low clock
                            end else case (stage)
                                G_ADDRW: begin     // -> register sub-address
                                    stage   <= G_REG;
                                    shreg   <= r_lat;
                                    bit_cnt <= 3'd0;
                                    sda_oe  <= ~r_lat[7];
                                    state   <= S_TX;
                                end
                                G_REG: begin
                                    if (!rw_lat) begin
                                        stage   <= G_WDATA;   // -> data byte
                                        shreg   <= w_lat;
                                        bit_cnt <= 3'd0;
                                        sda_oe  <= ~w_lat[7];
                                        state   <= S_TX;
                                    end else begin
                                        stage  <= G_ADDRR;    // -> reSTART
                                        sda_oe <= 1'b0;
                                        state  <= S_START;
                                    end
                                end
                                G_WDATA: begin     // write done -> STOP
                                    sda_oe <= 1'b1;
                                    state  <= S_STOP;
                                end
                                G_ADDRR: begin     // -> receive data byte
                                    stage   <= G_RDATA;
                                    bit_cnt <= 3'd0;
                                    sda_oe  <= 1'b0;
                                    state   <= S_RX;
                                end
                                default: begin     // unreachable
                                    sda_oe <= 1'b1;
                                    state  <= S_STOP;
                                end
                            endcase
                        end
                    endcase

                    // Receive one byte, MSB first (SDA released throughout)
                    S_RX: case (phase)
                        2'd0: scl   <= 1'b1;
                        2'd1: shreg <= {shreg[6:0], sda};   // sample mid-high
                        2'd2: scl   <= 1'b0;
                        2'd3: begin
                            if (bit_cnt == 3'd7) begin
                                rdata  <= shreg;
                                sda_oe <= 1'b0;    // NACK = SDA left high
                                state  <= S_MACK;
                            end else begin
                                bit_cnt <= bit_cnt + 3'd1;
                            end
                        end
                    endcase

                    // Master NACK slot (single-byte read: always NACK-last)
                    S_MACK: case (phase)
                        2'd0: scl <= 1'b1;
                        2'd1: ;
                        2'd2: scl <= 1'b0;
                        2'd3: begin
                            sda_oe <= 1'b1;        // STOP phase 0: SDA low
                            state  <= S_STOP;
                        end
                    endcase

                    // STOP: SDA rises while SCL is high, then bus-free time
                    S_STOP: case (phase)
                        2'd0: scl    <= 1'b1;      // SCL high, SDA still low
                        2'd1: sda_oe <= 1'b0;      // SDA release @ high: STOP
                        2'd2: ;                    // bus-free time
                        2'd3: begin
                            busy  <= 1'b0;
                            done  <= 1'b1;         // 1-cycle strobe
                            state <= S_IDLE;
                        end
                    endcase

                    default: state <= S_IDLE;
                endcase
            end
        end
    end

endmodule
