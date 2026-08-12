// ---------------------------------------------------------------------------
// i2c_slave_model.v -- reusable behavioural I2C slave for DRH-1 testbenches.
//
// TESTBENCH MODEL ONLY (event-driven, initial block, blocking assigns) -- not
// RTL, never synthesized. Kept standalone and generic so the integration TB
// (tb_top.v) can reuse it as the behavioural ADXL367 at 0x1D: parameterised
// 7-bit DEV_ADDR, a 256 x 8 register file, records the last written
// {reg, val} (and a running wr_count), serves reads from the file with an
// auto-incrementing pointer (the ADXL367 convention -- no bit7 trick, see
// firmware/twi.h's note), and ACKs ONLY its own address: any other address
// is ignored entirely and the model never touches the bus.
//
// Protocol served (matches firmware/twi.h's twi_reg_write / twi_reg_read):
//   write: START, addr+W [ACK], reg [ACK], data... [ACK each], STOP
//          (first byte after addr+W sets the pointer; later bytes are data,
//           written at ptr with post-increment)
//   read:  START, addr+W [ACK], reg [ACK], reSTART, addr+R [ACK],
//          data out... (continues while the master ACKs; master NACK ends it)
//
// Bus rules: SDA is open-drain -- the model only ever drives low or releases
// (assign sda = sda_drv ? 1'b0 : 1'bz). The TB must model the board's 4.7k
// pull-ups with a tb-side  pullup(sda);
// START (SDA falls, SCL high) re-arms address reception from ANY state, so
// repeated START works; STOP (SDA rises, SCL high) returns to idle.
// Inputs are sampled on posedge scl; the model changes what it drives only
// on negedge scl.
// ---------------------------------------------------------------------------

`timescale 1ns/1ps

module i2c_slave_model #(
    parameter [6:0] DEV_ADDR = 7'h1D       // ADXL367_ADDR on the card
) (
    input wire scl,
    inout wire sda
);

    // Open-drain SDA: drive low or release, never drive high.
    reg sda_drv;                            // 1 = drive SDA low
    assign sda = sda_drv ? 1'b0 : 1'bz;
    wire sda_in = (sda === 1'b0) ? 1'b0 : 1'b1;   // pullup resolves z -> 1

    // Register file + write record (read hierarchically by testbenches)
    reg [7:0] regs [0:255];
    reg [7:0] last_wr_reg;                  // last written register address
    reg [7:0] last_wr_val;                  // last written value
    integer   wr_count;                     // register writes seen (pointer
                                            //   byte does NOT count)

    localparam [2:0] I_IDLE = 3'd0,         // waiting for START
                     I_ADDR = 3'd1,         // shifting in address byte
                     I_ACKA = 3'd2,         // driving ACK for address
                     I_WR   = 3'd3,         // shifting in a written byte
                     I_ACKW = 3'd4,         // driving ACK for written byte
                     I_RD   = 3'd5,         // driving out a read byte
                     I_ACKR = 3'd6;         // sampling master ACK/NACK

    reg [2:0] state;
    reg [3:0] bitcnt;                       // bits received this byte
    reg [7:0] sh;                           // receive shift register
    reg [7:0] rd_sh;                        // transmit shift register
    reg [7:0] ptr;                          // register pointer
    reg [2:0] bitidx;                       // transmit bit index
    reg       rw_bit;                       // R/W bit of matched address
    reg       exp_ptr;                      // next written byte is the pointer
    reg       mack;                         // master ACKed the read byte

    integer i;
    initial begin
        state       = I_IDLE;
        sda_drv     = 1'b0;
        bitcnt      = 4'd0;
        sh          = 8'd0;
        rd_sh       = 8'd0;
        ptr         = 8'd0;
        bitidx      = 3'd0;
        rw_bit      = 1'b0;
        exp_ptr     = 1'b0;
        mack        = 1'b0;
        last_wr_reg = 8'h00;
        last_wr_val = 8'h00;
        wr_count    = 0;
        for (i = 0; i < 256; i = i + 1) regs[i] = 8'h00;
    end

    // START: SDA falls while SCL high -- (re)arms address reception from any
    // state, which is what makes the repeated START work.
    always @(negedge sda) if (scl === 1'b1) begin
        state   = I_ADDR;
        bitcnt  = 4'd0;
        sda_drv = 1'b0;
    end

    // STOP: SDA rises while SCL high.
    always @(posedge sda) if (scl === 1'b1) begin
        state   = I_IDLE;
        sda_drv = 1'b0;
    end

    // Sample on SCL rising edge.
    always @(posedge scl) begin
        case (state)
            I_ADDR, I_WR: begin
                sh     = {sh[6:0], sda_in};
                bitcnt = bitcnt + 4'd1;
            end
            I_ACKR: mack = ~sda_in;         // SDA low in the slot = master ACK
            default: ;
        endcase
    end

    // Drive / decide on SCL falling edge.
    always @(negedge scl) begin
        case (state)
            I_ADDR: if (bitcnt == 4'd8) begin
                if (sh[7:1] == DEV_ADDR) begin
                    rw_bit  = sh[0];
                    if (!sh[0]) exp_ptr = 1'b1;   // a write starts with the
                    sda_drv = 1'b1;               //   pointer byte
                    state   = I_ACKA;             // ACK own address only
                end else begin
                    state   = I_IDLE;             // not us: stay off the bus
                end
            end
            I_ACKA: begin
                if (rw_bit) begin                 // serve a read
                    rd_sh   = regs[ptr];
                    ptr     = ptr + 8'd1;         // auto-increment (ADXL367)
                    bitidx  = 3'd7;
                    sda_drv = ~rd_sh[7];          // MSB out right after ACK
                    state   = I_RD;
                end else begin
                    sda_drv = 1'b0;               // release ACK, receive
                    bitcnt  = 4'd0;
                    state   = I_WR;
                end
            end
            I_WR: if (bitcnt == 4'd8) begin
                if (exp_ptr) begin
                    ptr     = sh;                 // first byte = pointer
                    exp_ptr = 1'b0;
                end else begin
                    regs[ptr]   = sh;             // data byte: commit + record
                    last_wr_reg = ptr;
                    last_wr_val = sh;
                    wr_count    = wr_count + 1;
                    ptr         = ptr + 8'd1;     // post-increment
                end
                sda_drv = 1'b1;                   // ACK the byte
                bitcnt  = 4'd0;
                state   = I_ACKW;
            end
            I_ACKW: begin
                sda_drv = 1'b0;                   // release ACK
                state   = I_WR;                   // more data bytes welcome
            end
            I_RD: begin
                if (bitidx == 3'd0) begin
                    sda_drv = 1'b0;               // byte done: release for
                    mack    = 1'b0;               //   the master's ACK/NACK
                    state   = I_ACKR;
                end else begin
                    bitidx  = bitidx - 3'd1;
                    sda_drv = ~rd_sh[bitidx];     // next bit, MSB first
                end
            end
            I_ACKR: begin
                if (mack) begin                   // master ACKed: keep going
                    rd_sh   = regs[ptr];
                    ptr     = ptr + 8'd1;
                    bitidx  = 3'd7;
                    sda_drv = ~rd_sh[7];
                    state   = I_RD;
                end else begin
                    sda_drv = 1'b0;               // NACK: await STOP / START
                    state   = I_IDLE;
                end
            end
            default: ;
        endcase
    end

endmodule
