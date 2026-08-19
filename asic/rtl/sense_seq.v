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
 * vclamp -- THE BALLAST GUARD's measurement half (firmware: USE_BALLAST_GUARD,
 * GLOW_CLAMP_STO_MV in board.h, applied in sense.c's sense_glow_peak()). The
 * card clamps glow duty when the tank sits ABOVE 5200 mV, because at the abuse
 * corner (STO 5.5 V off a bench supply -- the AEM's own VOVCH 4.65 V never
 * reaches it -- min-bin Vf 1.9 V, VOL ~0.4 V) a held 100 % duty pushes RN1's
 * EXB-28V151JX elements to ~68-70 mW against a 62.5 mW rating. gamma_pwm
 * consumes this as clamp_en and caps peak duty at CLAMP_PEAK.
 *
 *   THRESHOLD, and how provisional it is: TH_LOW/TH_CRIT are tagged
 *   "placeholder scaling" and TH_CLAMP inherits exactly that caveat -- it is
 *   derived FROM them, not from volts, so the three move together and cannot
 *   drift apart. TH_LOW 96 stands for the firmware's VS_GLOW_FLOOR_MV 2750,
 *   which implies 2750/96 = 28.65 mV per code; GLOW_CLAMP_STO_MV 5200 is then
 *   5200/28.65 = 181.5, and TH_CLAMP takes the FLOOR, 181. Flooring is the
 *   conservative rounding for a guard: the clamp engages at code 181 (~5185 mV
 *   on that scale), at or below the threshold it is protecting, never above it.
 *   Sanity, since a threshold past full scale would be silently unreachable:
 *   181 of 255 is 71 % of range, and even the 5.5 V abuse corner is code 192.
 *
 *   POLARITY is deliberately the opposite kind from vlow/vcrit. Those are
 *   STRICT-below flags; vclamp is AT-OR-ABOVE, so the three partition the
 *   range with no gap and no overlap, and the firmware's strict `mv >
 *   GLOW_CLAMP_STO_MV` is preserved with the rounding folded into TH_CLAMP.
 *
 *   RESET IS PESSIMISTIC (vclamp <= 1), and this is the one place this module
 *   deliberately breaks its own optimistic-reset rule. The rule exists because
 *   an unmeasured LOW should not block the first tap -- costing a glow that
 *   should have happened. An unmeasured HIGH costs the opposite: ballast
 *   over-dissipation on a part already at 110 % of rating at the corner. The
 *   failure directions are opposite, so the safe reset values are too. It is
 *   not theoretical -- wake_fsm's IDLE will glow on a tap using the STANDING
 *   latches, before the force_rd sample it triggers has landed, so a glow
 *   genuinely can precede the first conversion.
 *
 *   BOTH stuck-analog directions stay safe, which is worth stating because
 *   only one of them is obvious: stuck-at-0 sets vlow+vcrit -> DORMANT -> mode
 *   00 -> no LED current at all, and stuck-at-full sets vclamp -> clamped.
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
    parameter [7:0] TH_LOW   = 8'd96,    // vlow:   below glow floor  (placeholder scaling)
    parameter [7:0] TH_CRIT  = 8'd64,    // vcrit:  brownout floor
    parameter [7:0] TH_CLAMP = 8'd181    // vclamp: ballast guard     (see header)
)(
    input  wire clk, input wire rst_n,
    input  wire tick_poll, input wire tick_env,
    input  wire force_rd,                // event path: tap is about to spend a glow
    input  wire [7:0] sar_result, input wire sar_done,
    output reg  sar_go, output reg sns_en,
    output reg  [7:0] sto_q, output reg vlow, output reg vcrit,
    output reg  vclamp                   // rail high enough that RN1 needs the duty clamp
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
            vclamp   <= 1'b1;            // PESSIMISTIC on purpose -- see header
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
                        vlow   <= (sar_result <  TH_LOW);
                        vcrit  <= (sar_result <  TH_CRIT);
                        vclamp <= (sar_result >= TH_CLAMP);
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
