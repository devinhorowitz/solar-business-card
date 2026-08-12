/*
 * sense_seq.v -- DRH-1 companion ASIC: gated STO sense-divider sequencer
 *                (SPEC.md port contract -- do not deviate).
 *
 * Firmware mirror: firmware/sense.c -- sense_vmin_tick()'s DEFERRED-READ
 * pattern plus sto_raw()'s event path, and the board.h SNS_EN/U10 rule.
 * On the card the R15/R16 divider only exists while a conversion needs it:
 * U10 (TPS22916, SNS_EN on PC0) gates it, because left connected it bleeds
 * 1.55 uA from the tank forever -- the largest single line in the standby
 * ledger. The firmware's periodic path arms the gate on one poll and samples
 * on a later tick so the RC settle elapses while the MCU sleeps; the event
 * path (a tap about to spend a glow) reads immediately. This module is that
 * sequencing in silicon:
 *
 *   IDLE -> (every POLLS_PER_SAMPLE-th tick_poll, or force_rd) ARM (sns_en=1)
 *        -> SETTLE (count SETTLE_ENV_TICKS+1 tick_env strobes: C24 through
 *           the 667k Thevenin, the ~33 ms/5-tau wait of board.h
 *           STO_SNS_SETTLE_MS -- see the settle-arithmetic note below)
 *        -> CONVERT (sar_go 1-cycle strobe, wait sar_done)
 *        -> LATCH (sto_q/vlow/vcrit updated) -> IDLE with sns_en=0.
 *
 * Settle arithmetic (why +1): ARM lands asynchronously to tick_env -- the
 * periodic path fires on tick_poll and force_rd whenever the event does --
 * so the first strobe observed after ARM may close a PARTIAL env period
 * (worst case, it arrives 1 clk later and closes ~0 of one). Observing k
 * strobes from ARM therefore guarantees only k-1 FULL periods have elapsed.
 * SETTLE counts SETTLE_ENV_TICKS+1 strobes, so the guaranteed settle is
 * >= SETTLE_ENV_TICKS full env periods (~39 ms at 128 Hz with the default 5)
 * on BOTH the periodic and the force paths. (Counting SETTLE_ENV_TICKS
 * strobes -- the obvious reading -- guarantees only SETTLE_ENV_TICKS-1.)
 *
 * The divider is gated OFF between samples -- that is the entire point of
 * the U10 chain this replaces: sns_en's duty is one settle+conversion per
 * POLLS_PER_SAMPLE polls (~47 ms + 16 us per 16 s at real scaling, ~0.3%:
 * SETTLE_ENV_TICKS+1 = 6 strobes at 128 Hz), and the testbench asserts that
 * bound.
 *
 * Latch ordering: sto_q/vlow/vcrit are written at the edge ENTERING LATCH
 * (the sar_done handshake edge, sar_ctrl's result already registered), and
 * sns_en falls one cycle later leaving LATCH -- the gate drops strictly
 * AFTER the latch, mirroring sto_raw()'s read-then-OUTCLR order.
 *
 * Flag semantics (firmware polarity, sense.c rail gates): vlow/vcrit are
 * STRICT below-threshold flags -- vlow = (sample < TH_LOW), the complement
 * of sense_rail_ok()'s (raw >= RAIL_COUNT). A sample equal to the threshold
 * is NOT low. Flags persist between samples and reset to 0 (optimistic:
 * dormancy is entered on a MEASURED low, as in main.c, so the first tap
 * after reset is not blocked by a phantom vcrit; a stuck-at-0 analog chain
 * still converts to result 0 -> vlow/vcrit set -> no glow, the same
 * fail-safe direction as the firmware's stuck-ADC-reads-0 rule).
 *
 * force_rd is sampled in IDLE only; a pulse during an in-flight sample is
 * absorbed (the running sample is equally fresh -- the same collapse of
 * doubled reads sto_raw() gets by disarming the deferred sampler). Starting
 * any sample restarts the POLLS_PER_SAMPLE cadence.
 *
 * Verilog-2001, single clock, synchronous reset (rst_n sampled on posedge
 * clk), no latches, no initial blocks, strobes exactly 1 clk wide.
 */
module sense_seq #(
    parameter SETTLE_ENV_TICKS = 5,      // ~39 ms at 128 Hz -- the RC settle, in silicon
    parameter POLLS_PER_SAMPLE = 16,     // sense.c's VMIN_SAMPLE_POLLS
    parameter [7:0] TH_LOW  = 8'd96,     // vlow: below glow floor   (placeholder scaling)
    parameter [7:0] TH_CRIT = 8'd64      // vcrit: brownout floor
)(
    input  wire clk, input wire rst_n,
    input  wire tick_poll, input wire tick_env,
    input  wire force_rd,                // event path: tap is about to spend a glow
    input  wire [7:0] sar_result, input wire sar_done,
    output reg  sar_go, output reg sns_en,
    output reg  [7:0] sto_q, output reg vlow, output reg vcrit
);

    // constant fn (Verilog-2001) so counters are sized, not blanket 32 bits
    function integer clog2 (input integer value);
        integer v;
        begin
            v = value - 1;
            for (clog2 = 0; v > 0; clog2 = clog2 + 1)
                v = v >> 1;
        end
    endfunction

    localparam integer PW = (POLLS_PER_SAMPLE < 2) ? 1 : clog2(POLLS_PER_SAMPLE);
    localparam integer EW = (SETTLE_ENV_TICKS < 1) ? 1 : clog2(SETTLE_ENV_TICKS + 1);

    localparam [PW-1:0] PLIM = POLLS_PER_SAMPLE - 1;   // arm on the PLIM+1-th poll
    localparam [EW-1:0] ELIM = SETTLE_ENV_TICKS;       // convert on the ELIM+1-th env
                                                       //   strobe: k strobes observed
                                                       //   = k-1 full periods (header)

    localparam [2:0] S_IDLE    = 3'd0,
                     S_ARM     = 3'd1,
                     S_SETTLE  = 3'd2,
                     S_CONVERT = 3'd3,
                     S_LATCH   = 3'd4;

    reg [2:0]    state;
    reg [PW-1:0] poll_cnt;   // tick_polls since the last sample started
    reg [EW-1:0] env_cnt;    // tick_envs settled so far this sample

    always @(posedge clk) begin
        if (!rst_n) begin
            state    <= S_IDLE;
            poll_cnt <= {PW{1'b0}};
            env_cnt  <= {EW{1'b0}};
            sar_go   <= 1'b0;
            sns_en   <= 1'b0;
            sto_q    <= 8'd0;
            vlow     <= 1'b0;
            vcrit    <= 1'b0;
        end else begin
            sar_go <= 1'b0;                        // 1-cycle strobe

            // poll cadence: count every tick_poll (saturating -- a sample is
            // ~40 ms against a 1 s poll, so saturation is unreachable, but no
            // counter here may wrap); cleared below when a sample starts.
            if (tick_poll && poll_cnt != PLIM)
                poll_cnt <= poll_cnt + 1'b1;

            case (state)
                S_IDLE:
                    if (force_rd || (tick_poll && poll_cnt == PLIM)) begin
                        state    <= S_ARM;
                        sns_en   <= 1'b1;          // divider ON (U10 gate)
                        poll_cnt <= {PW{1'b0}};    // restart the cadence
                        env_cnt  <= {EW{1'b0}};
                    end

                S_ARM:                             // gate just closed; settle from here
                    state <= S_SETTLE;

                S_SETTLE:
                    if (tick_env) begin
                        if (env_cnt == ELIM) begin
                            state  <= S_CONVERT;
                            sar_go <= 1'b1;        // start the SAR (1-cycle strobe)
                        end else begin
                            env_cnt <= env_cnt + 1'b1;
                        end
                    end

                S_CONVERT:
                    if (sar_done) begin            // latch at the handshake edge
                        sto_q <= sar_result;
                        vlow  <= (sar_result < TH_LOW);
                        vcrit <= (sar_result < TH_CRIT);
                        state <= S_LATCH;
                    end

                S_LATCH: begin                     // one cycle: gate drops AFTER latch
                    sns_en <= 1'b0;                // divider OFF -> zero tank draw
                    state  <= S_IDLE;
                end

                default: begin                     // illegal state: recover gated-off
                    state  <= S_IDLE;
                    sns_en <= 1'b0;
                end
            endcase
        end
    end

endmodule
