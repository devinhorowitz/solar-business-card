/*
 * init_seq.v -- DRH-1 companion ASIC: ADXL367 configuration sequencer.
 *
 * MIRRORS firmware/adxl367.c (SPEC.md names it "accel.c" -- there is no file of
 * that name; adxl367_init_tap() is the config-and-verify bring-up this module
 * reproduces): a fixed sequence of single-register I2C writes to the ADXL367
 * at 7-bit address 0x1D (ASEL grounded on the card, see firmware/board.h),
 * config-before-MEASURE order with POWER_CTL flipped last, exactly as the
 * data-sheet rule the firmware follows.
 *
 * ROM (8 entries -- SPEC allows 6-8; the card writes 14). Values are copied
 * from firmware/adxl367.h's ADXL_CFG_* constants and are ALL PROVISIONAL,
 * same as their firmware sources ("BARE-CARD starting points; bench-tune"):
 *
 *   idx  reg   val   register        source / note
 *   ---  ----  ----  --------------  ------------------------------------------
 *    0   0x1F  0x52  SOFT_RESET      ADXL_SOFT_RESET_CODE ('R'). PROVISIONAL
 *                                    SIMPLIFICATION: the data sheet's 7.5 ms
 *                                    post-reset latency (adxl367.c waits 10 ms)
 *                                    is NOT modelled -- no settle counter here;
 *                                    v-next if a real part ever hangs off this.
 *    1   0x2C  0x23  FILTER_CTL      ADXL_CFG_FILTER_CTL: +/-2 g, 100 Hz.
 *    2   0x2F  0x30  TAP_THRESH      ADXL_CFG_TAP_THRESH (PROVISIONAL, tune).
 *    3   0x30  0x10  TAP_DUR         ADXL_CFG_TAP_DUR: 10 ms max tap width.
 *    4   0x43  0x20  AXIS_MASK       ADXL_CFG_AXIS_MASK: tap on Z.
 *    5   0x3A  0x01  INTMAP1_UPPER   ADXL_CFG_INTMAP1_UPPER: TAP_ONE -> INT1.
 *    6   0x2B  0x10  INTMAP2_LOWER   ADXL_CFG_INTMAP2_LOWER: ACT -> INT2.
 *    7   0x2D  0x0A  POWER_CTL       PROVISIONAL: WAKEUP(bit3)=1 + MEASURE=10,
 *                                    the "wake-up mode" SPEC.md asks for. The
 *                                    CARD runs 0x02 (always-measurement, no
 *                                    wake-up -- adxl367.h documents why); the
 *                                    deviation is per SPEC, tagged here.
 *   Dropped vs the card's 14 writes (the 8-entry cap): TAP_LATENT/TAP_WINDOW
 *   (hardware double-tap timing -- wake_fsm.v resolves the second tap itself,
 *   so the hw double-tap engine is not needed), THRESH_ACT_H/L, TIME_ACT,
 *   ACT_INACT_CTL (activity engine; int2 is reserved in wake_fsm v1). The
 *   firmware's ID read-back verify (adxl367_present) is also not carried:
 *   this sequencer is write-only; ack_err is the "device not talking" tell.
 *
 * Handshake (one i2c_master transaction per ROM entry): m_start is a 1-clk
 * strobe; m_reg/m_wdata are held stable until the next issue; completion is
 * the master's m_done strobe with m_ack_err valid in the same cycle (the
 * master's ack_err is a level that persists to done -- SPEC i2c_master).
 * m_busy is unused by this FSM (m_done alone sequences it) but belongs to
 * the contract and lets a testbench stub the master directly.
 *
 * Error policy (SPEC): any m_ack_err -> retry the SAME entry once; a second
 * consecutive m_ack_err on that entry -> fail=1, park. The retry budget is
 * per entry (a successful handshake re-arms it), matching the "retry once,
 * then park" reading the TB pins down: one NACK + clean retry -> fail stays
 * 0 and the sequence completes; two NACKs on one entry -> fail=1, done_all
 * stays 0, no further entries are issued.
 *
 * done_all and fail are STICKY LEVELS (not strobes): done_all is drh1_top's
 * init_done into wake_fsm, which needs a level to leave WAIT_INIT and hold.
 * active is high from the accepted start until done/park. A new start pulse
 * while parked (done or failed) re-runs the whole sequence and clears both
 * flags -- drh1_top only ever starts it once, but the hook costs nothing.
 *
 * Verilog-2001, single clock, synchronous rst_n, no latches, no initial in
 * RTL, strobes exactly one clk wide (SPEC.md global rules).
 */
module init_seq (
    input  wire clk, input wire rst_n, input wire start,
    output reg  active, output reg done_all, output reg fail,
    output reg  m_start, output reg [6:0] m_dev, output reg m_rw,
    output reg  [7:0] m_reg, output reg [7:0] m_wdata,
    input  wire m_busy, input wire m_done, input wire m_ack_err
);

    localparam [6:0] DEV_ADDR = 7'h1D;   // ADXL367, ASEL grounded (board.h)
    localparam integer N = 8;            // ROM entries (SPEC: 6-8)

    // {reg_addr, value} ROM -- see the table in the header. Values PROVISIONAL.
    function [15:0] rom (input [2:0] i);
        begin
            case (i)
                3'd0:    rom = {8'h1F, 8'h52};   // SOFT_RESET  <- 'R'
                3'd1:    rom = {8'h2C, 8'h23};   // FILTER_CTL  +/-2 g, 100 Hz
                3'd2:    rom = {8'h2F, 8'h30};   // TAP_THRESH  (PROVISIONAL)
                3'd3:    rom = {8'h30, 8'h10};   // TAP_DUR     10 ms
                3'd4:    rom = {8'h43, 8'h20};   // AXIS_MASK   tap on Z
                3'd5:    rom = {8'h3A, 8'h01};   // INTMAP1_UPPER: tap -> INT1
                3'd6:    rom = {8'h2B, 8'h10};   // INTMAP2_LOWER: act -> INT2
                3'd7:    rom = {8'h2D, 8'h0A};   // POWER_CTL   wake-up+measure (PROVISIONAL)
                default: rom = {8'h1F, 8'h52};   // unreachable (N == 8)
            endcase
        end
    endfunction

    localparam [0:0] S_IDLE = 1'd0,      // not running: reset state AND park
                     S_WAIT = 1'd1;      // entry issued, waiting for m_done

    reg       state;
    reg [2:0] idx;                       // current ROM entry, 0..N-1
    reg       retried;                   // current entry already retried once

    always @(posedge clk) begin
        if (!rst_n) begin
            state    <= S_IDLE;
            idx      <= 3'd0;
            retried  <= 1'b0;
            active   <= 1'b0;
            done_all <= 1'b0;
            fail     <= 1'b0;
            m_start  <= 1'b0;
            m_dev    <= DEV_ADDR;        // constant: this chip talks to one device
            m_rw     <= 1'b0;            // write-only sequencer
            m_reg    <= 8'd0;
            m_wdata  <= 8'd0;
        end else begin
            m_start <= 1'b0;             // default: m_start is a 1-clk strobe

            case (state)

                // Waiting to be kicked (covers both power-on and post-run park;
                // done_all / fail hold their last values until a new start).
                S_IDLE: begin
                    if (start) begin
                        idx      <= 3'd0;
                        retried  <= 1'b0;
                        done_all <= 1'b0;
                        fail     <= 1'b0;
                        active   <= 1'b1;
                        {m_reg, m_wdata} <= rom(3'd0);
                        m_start  <= 1'b1;
                        state    <= S_WAIT;
                    end
                end

                // One transaction in flight; m_done resolves it.
                S_WAIT: begin
                    if (m_done) begin
                        if (m_ack_err) begin
                            if (!retried) begin
                                retried <= 1'b1;
                                m_start <= 1'b1;     // reissue the SAME entry
                            end else begin
                                fail   <= 1'b1;      // two NACKs on one entry
                                active <= 1'b0;
                                state  <= S_IDLE;    // park (done_all stays 0)
                            end
                        end else begin
                            retried <= 1'b0;         // success re-arms the retry
                            if (idx == N - 1) begin
                                done_all <= 1'b1;    // sticky: top's init_done
                                active   <= 1'b0;
                                state    <= S_IDLE;  // park
                            end else begin
                                idx <= idx + 3'd1;
                                {m_reg, m_wdata} <= rom(idx + 3'd1);
                                m_start <= 1'b1;
                            end
                        end
                    end
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
