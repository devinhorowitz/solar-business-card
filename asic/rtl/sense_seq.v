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
 *   THRESHOLD: 5200 mV from board.h, converted by the one scale this module
 *   declares -- see THE ANALOG CONTRACT below.
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
 * THE ANALOG CONTRACT (pinned 2026-08-19; TH_LOW/TH_CRIT carried a "placeholder
 * scaling" tag from this module's first commit until then, and TH_CLAMP had to be
 * derived from TH_LOW rather than from volts, because there was no scale to use).
 *
 *   FULL SCALE. One code is FS_MV/256 of STO. FS_MV = 6000 realises as a /5 on-die
 *   divider into a 1.2 V bandgap reference -- a 4R:R ratio in hi-res poly, which is
 *   what the absorb map moves R15/R16 into -- giving 23.4 mV per code. The card's own
 *   chain is /3 into 2.048 V at 12 bits (1.5 mV per code); this is ~16x coarser, which
 *   is fine against thresholds hundreds of mV apart and is the price of an 8-bit SAR.
 *
 *   WHY 6000 AND NOT 4650. The obvious full scale is the AEM10300's VOVCH ceiling,
 *   since STO physically lives in 0.20-4.65 V (STO_CFG[3:0] = LLHH straps VOVCH 4.65 /
 *   VCHRDY 1.00 / VOVDIS 0.20, read off the board file). It would be WRONG.
 *   GLOW_CLAMP_STO_MV is 5200 -- ABOVE VOVCH -- because the ballast guard exists for an
 *   abuse corner reachable only from a bench supply, and a converter saturating at
 *   4.65 V could never see it: the guard would be unreachable, silently, and every
 *   bench would still pass. 6000 mV clears the 5.5 V supercap rating with headroom.
 *
 *   AND IT PAYS A DIVIDEND THE BOARD ALREADY CLAIMED: board.h says of the clamp
 *   threshold "(VOVCH 4.65 V never trips it)". On this scale VOVCH is code 198 and
 *   TH_CLAMP is 221, so that sentence becomes a property of the silicon rather than a
 *   parenthetical -- and tb_sense_seq asserts it.
 *
 *   PROVENANCE, one line each, because the three are NOT equally solid:
 *     TH_LOW_MV   2750  board.h VS_GLOW_FLOOR_MV. Solid -- vlow is defined as the
 *                       complement of sense_rail_ok(), which gates on exactly this.
 *     TH_CLAMP_MV 5200  board.h GLOW_CLAMP_STO_MV. Solid, same file, same reason.
 *     TH_CRIT_MV  2000  AN ASIC-SIDE CHOICE, and it must not be read as a firmware
 *                       mirror: THE CARD HAS NO SECOND RAIL GATE. main.c gates every
 *                       glow at VS_GLOW_FLOOR_MV and stops there; the latching DORMANT
 *                       state below it is this design's own addition, so its floor
 *                       needs its own basis. It takes the pack's usable-depth floor
 *                       from the AEM10300 selection analysis ("drain to ~2 V at the
 *                       load -> ~9-10 J usable"), i.e. the point the energy budget
 *                       already treats as spent. Below the 2750 glow gate, as the
 *                       ordering requires, and far above VCHRDY 1.00 V, where nothing
 *                       runs at all. Revisit with bench data, not by argument.
 *
 * Verilog-2001, single clock, synchronous reset (rst_n sampled on posedge
 * clk), no latches, no initial blocks, strobes exactly 1 clk wide.
 */
module sense_seq #(
    parameter SETTLE_ENV_TICKS = 5,      // ~39 ms at 128 Hz -- the RC settle, in silicon
    parameter POLLS_PER_SAMPLE = 16,     // sense.c's VMIN_SAMPLE_POLLS
    // ---- THE ANALOG CONTRACT: what one code is worth, in millivolts of STO ----
    // Thresholds are given in MILLIVOLTS and the codes are derived below, so every
    // number here can be checked against board.h instead of against a scale factor
    // nobody wrote down. See the header for the full-scale derivation and sources.
    parameter integer FS_MV       = 6000, // STO at full scale: /5 divider, 1.2 V bandgap
    parameter integer TH_LOW_MV   = 2750, // board.h VS_GLOW_FLOOR_MV -- the card's glow gate
    parameter integer TH_CRIT_MV  = 2000, // pack usable-depth floor -- an ASIC-SIDE choice
    parameter integer TH_CLAMP_MV = 5200  // board.h GLOW_CLAMP_STO_MV -- the ballast guard
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

    /* CODES ARE DERIVED, and each rounds in the direction that makes the PROTECTIVE
     * action happen sooner rather than later:
     *   vlow / vcrit are strict-BELOW gates, so rounding UP (ceil) means the glow is
     *     withheld, or dormancy entered, a fraction of an LSB early.
     *   vclamp is an AT-OR-ABOVE gate, so rounding DOWN (floor) means the ballast
     *     ceiling engages a fraction of an LSB early.
     * One LSB is FS_MV/256 = 23.4 mV at the default scale, so the bias is small; the
     * point is that it is deliberate and always in the safe direction. */
    localparam [7:0] TH_LOW   = (TH_LOW_MV   * 256 + FS_MV - 1) / FS_MV;   // ceil
    localparam [7:0] TH_CRIT  = (TH_CRIT_MV  * 256 + FS_MV - 1) / FS_MV;   // ceil
    localparam [7:0] TH_CLAMP = (TH_CLAMP_MV * 256)             / FS_MV;   // floor

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
