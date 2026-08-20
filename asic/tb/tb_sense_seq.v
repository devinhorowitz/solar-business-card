/*
 * tb_sense_seq.v -- self-checking testbench for sense_seq + sar_ctrl (DRH-1).
 *
 * Wires sar_ctrl to a behavioural comparator, cmp_in = (VIN_CODE > dac_code)
 * with VIN_CODE a tb register -- exactly the SPEC comparator convention --
 * and sense_seq to sar_ctrl (sar_go -> go, done/result -> sar_done/sar_result),
 * so the whole gated-sense chain of firmware/sense.c is proven end to end.
 *
 * Tick scaling: same clkdiv structure and exact 128:1 env:poll ratio, shrunk
 * (32 clk per tick_env, 4096 clk per tick_poll) so a 32-poll run is ~131k
 * cycles. The duty ratio this produces (~0.3%) is the same order as the real
 * card's (~39 ms settle + 16 us conversion per 16 s = ~0.25%).
 *
 * Checks (all $fatal on failure -- real properties, not just activity):
 *   A. SAR alone (ticks off, sense_seq idle; tb drives go): result equals
 *      VIN_CODE EXACTLY for 0, 64, 96, 200, 255; busy high throughout; done
 *      latency 16 clk (8 bits x 2 clk, window 14..20 asserted); done a
 *      1-cycle strobe; busy low in the done cycle.
 *   B. Cadence + duty: from reset, sns_en continuously LOW for polls 1..15
 *      (asserted every cycle) and the first sample starts on the 16th poll;
 *      low again for polls 17..31, second sample on the 32nd. Per sample:
 *      sar_go fires after exactly SETTLE_ENV_TICKS+1(=6) tick_env strobes
 *      with sns_en high (observing k strobes guarantees k-1 full periods, so
 *      the settle is >= SETTLE_ENV_TICKS full env periods even though ARM is
 *      async to tick_env -- the sense_seq header's arithmetic, pinned here),
 *      exactly one sar_go and one sar_done inside the high window,
 *      sto_q latched BEFORE sns_en falls, high-time bounded. Then THE DUTY
 *      GATE -- the U10 deferred-read property from sense.c, the entire
 *      reason the chain exists: total sns_en-high clk cycles over the full
 *      32-poll run < 2% of elapsed cycles, with exactly 2 conversions.
 *   C. force_rd + thresholds: 3 polls into a 16-poll cadence, force_rd makes
 *      sns_en rise within 4 cycles (immediate, out of cadence). vlow/vcrit
 *      latch per sample: 95 -> vlow only; 63 -> both; boundaries 64 (vcrit
 *      clear: not strictly below) and 96 (vlow clear); 200 -> both clear
 *      (recovery). sto_q exact each time.
 *
 * All TB sampling is on negedge clk: NBA-updated DUT state is stable. A
 * monitor block additionally rejects X on sns_en/sar_go/done/busy and any
 * sar_go or done strobe wider than 1 cycle, everywhere in the run.
 */
`timescale 1ns/1ps

module tb_sense_seq;

    // tick scaling -- clkdiv's exact 128:1 structure, shrunk for sim speed
    localparam integer ENV_CLKS  = 32;                   // clk per tick_env
    localparam integer POLL_ENVS = 128;                  // tick_envs per tick_poll
    localparam integer POLL_CLKS = ENV_CLKS * POLL_ENVS; // 4096 clk per tick_poll

    localparam integer SETTLE  = 5;      // = DUT SETTLE_ENV_TICKS
    localparam integer PPS     = 16;     // = DUT POLLS_PER_SAMPLE
    /* THE ANALOG CONTRACT, driven from here so the bench owns it (sense_seq's own
     * defaults are the same numbers). The CODES below are re-derived independently
     * with the same rounding rule the DUT states -- if the two disagree, C2's
     * boundary cases fail. Check D then goes further and validates the boundaries
     * in MILLIVOLTS, which is what catches the rounding rule itself being wrong in
     * both places at once. */
    localparam integer FS_MV       = 6000;   // /5 divider into a 1.2 V bandgap
    localparam integer TH_LOW_MV   = 2750;   // board.h VS_GLOW_FLOOR_MV
    localparam integer TH_CRIT_MV  = 2000;   // pack usable-depth floor (ASIC-side)
    localparam integer TH_CLAMP_MV = 5200;   // board.h GLOW_CLAMP_STO_MV
    localparam integer VOVCH_MV    = 4650;   // AEM10300 ceiling, STO_CFG = LLHH

    localparam [7:0] TH_LOW   = (TH_LOW_MV   * 256 + FS_MV - 1) / FS_MV;  // ceil
    localparam [7:0] TH_CRIT  = (TH_CRIT_MV  * 256 + FS_MV - 1) / FS_MV;  // ceil
    localparam [7:0] TH_CLAMP = (TH_CLAMP_MV * 256)             / FS_MV;  // floor
    localparam [7:0] VOVCH_C  = (VOVCH_MV    * 256)             / FS_MV;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    // ---------------- tick generator (mirrors clkdiv, gate-able) ----------------
    reg        tick_en = 1'b0;
    reg        tick_env, tick_poll;
    reg [7:0]  envc;
    reg [7:0]  env_of_poll;
    always @(posedge clk) begin
        if (!rst_n || !tick_en) begin
            envc <= 8'd0; env_of_poll <= 8'd0;
            tick_env <= 1'b0; tick_poll <= 1'b0;
        end else begin
            tick_env <= 1'b0; tick_poll <= 1'b0;
            if (envc == ENV_CLKS - 1) begin
                envc     <= 8'd0;
                tick_env <= 1'b1;
                if (env_of_poll == POLL_ENVS - 1) begin
                    env_of_poll <= 8'd0;
                    tick_poll   <= 1'b1;   // poll coincides with an env, as in clkdiv
                end else begin
                    env_of_poll <= env_of_poll + 8'd1;
                end
            end else begin
                envc <= envc + 8'd1;
            end
        end
    end

    // ---------------- DUT chain ----------------
    reg        force_rd = 1'b0;
    reg        tb_go    = 1'b0;          // phase-A direct SAR drive (sense_seq idle)
    reg [7:0]  VIN_CODE = 8'd0;          // the "analog" rail the comparator sees

    wire       seq_go, sns_en, vlow, vcrit, vclamp;
    wire [7:0] sto_q, dac_code, sar_result;
    wire       sar_done, sar_busy;

    wire cmp_in = (VIN_CODE > dac_code); // behavioural comparator, per SPEC

    sense_seq #(
        .SETTLE_ENV_TICKS(SETTLE), .POLLS_PER_SAMPLE(PPS),
        .FS_MV(FS_MV), .TH_LOW_MV(TH_LOW_MV),
        .TH_CRIT_MV(TH_CRIT_MV), .TH_CLAMP_MV(TH_CLAMP_MV)
    ) u_seq (
        .clk(clk), .rst_n(rst_n),
        .tick_poll(tick_poll), .tick_env(tick_env),
        .force_rd(force_rd),
        .sar_result(sar_result), .sar_done(sar_done),
        .sar_go(seq_go), .sns_en(sns_en),
        .sto_q(sto_q), .vlow(vlow), .vcrit(vcrit), .vclamp(vclamp)
    );

    sar_ctrl u_sar (
        .clk(clk), .rst_n(rst_n),
        .go(seq_go | tb_go),
        .cmp_in(cmp_in),
        .dac_code(dac_code),
        .result(sar_result), .done(sar_done), .busy(sar_busy)
    );

    // watchdog: whole run is ~150k cycles = 1.5 ms sim time
    initial begin
        #20_000_000;
        $fatal(1, "TB TIMEOUT: did not reach TB PASS");
    end

    // ---------------- always-on monitor: X + strobe-width + duty ----------------
    integer mon_cycles, mon_high, mon_go, mon_done;
    reg     mon_en = 1'b0;
    reg     prev_go_m = 1'b0, prev_done_m = 1'b0;
    always @(negedge clk) begin
        if (sns_en === 1'bx)   $fatal(1, "sns_en is X");
        if (seq_go === 1'bx)   $fatal(1, "sar_go is X");
        if (sar_done === 1'bx) $fatal(1, "sar done is X");
        if (sar_busy === 1'bx) $fatal(1, "sar busy is X");
        if (seq_go === 1'b1 && prev_go_m)
            $fatal(1, "sar_go wider than 1 cycle -- not a strobe");
        if (sar_done === 1'b1 && prev_done_m)
            $fatal(1, "sar done wider than 1 cycle -- not a strobe");
        prev_go_m   = (seq_go === 1'b1);
        prev_done_m = (sar_done === 1'b1);
        if (mon_en) begin
            mon_cycles = mon_cycles + 1;
            if (sns_en === 1'b1)   mon_high = mon_high + 1;
            if (seq_go === 1'b1)   mon_go   = mon_go + 1;
            if (sar_done === 1'b1) mon_done = mon_done + 1;
        end
    end

    // ---------------- helpers ----------------
    task do_reset;
        begin
            @(negedge clk);
            rst_n = 1'b0;
            repeat (4) @(negedge clk);
            rst_n = 1'b1;
        end
    endtask

    // one direct SAR conversion (phase A): exact result + timing contract
    task sar_conv;
        input [7:0] v;
        integer lat;
        begin
            VIN_CODE = v;
            @(negedge clk); tb_go = 1'b1;
            @(negedge clk); tb_go = 1'b0;
            lat = 0;
            while (sar_done !== 1'b1) begin
                @(negedge clk);
                lat = lat + 1;
                if (sar_done !== 1'b1 && sar_busy !== 1'b1)
                    $fatal(1, "SAR busy dropped mid-conversion (VIN=%0d, lat %0d)", v, lat);
                if (lat > 40)
                    $fatal(1, "SAR done timeout for VIN=%0d", v);
            end
            if (lat < 14 || lat > 20)
                $fatal(1, "SAR latency %0d clk outside 14..20 (expect 16 = 8 bits x 2 clk)", lat);
            if (sar_result !== v)
                $fatal(1, "SAR result %0d != VIN_CODE %0d -- no exact convergence", sar_result, v);
            if (sar_busy !== 1'b0)
                $fatal(1, "SAR busy still high in the done cycle");
            @(negedge clk);
            if (sar_done !== 1'b0)
                $fatal(1, "SAR done not a 1-cycle strobe");
        end
    endtask

    // land on a negedge inside a tick_env strobe cycle (so a force_rd issued
    // right after never races the next env tick -- keeps env_at_go exact)
    task sync_env;
        begin
            @(negedge clk);
            while (tick_env !== 1'b1) @(negedge clk);
        end
    endtask

    task pulse_force;
        begin
            sync_env;
            @(negedge clk); force_rd = 1'b1;
            @(negedge clk); force_rd = 1'b0;
        end
    endtask

    // observe one full sample: rise (within max_wait), settle/convert/latch
    // shape, fall, and the latched outputs
    /* one forced sample at `code`, returning the resulting vclamp. Used by D to
     * DISCOVER sense_seq's clamp threshold rather than restate it: TH_LOW/TH_CRIT
     * are overridden above, TH_CLAMP deliberately is not, so a changed default is
     * still under test instead of being silently agreed with. */
    integer d_lo, d_hi, d_mid;
    integer b_low, b_crit, b_clamp;   // discovered boundaries, for the ordering check
    reg     d_cl;

    /* a discovered boundary code, checked against its millivolt target. `up` selects
     * the rounding the threshold is supposed to use: 1 = ceil (vlow/vcrit, protective
     * = trip early on the way down), 0 = floor (vclamp, protective = clamp early on
     * the way up). Both must land strictly inside one LSB of the target. */
    task check_volts;
        input [8*5:1] name;
        input integer code;
        input integer target_mv;
        input integer up;
        integer mv, lsb;
        begin
            mv  = (code * FS_MV) / 256;
            lsb = FS_MV / 256;
            if (up) begin
                if (mv < target_mv)
                    $fatal(1, "D: %0s boundary code %0d = %0d mV is BELOW its %0d mV target -- rounded the unsafe way",
                           name, code, mv, target_mv);
                if (mv - target_mv >= lsb)
                    $fatal(1, "D: %0s boundary code %0d = %0d mV is more than one LSB (%0d mV) above %0d mV",
                           name, code, mv, lsb, target_mv);
            end else begin
                if (mv > target_mv)
                    $fatal(1, "D: %0s boundary code %0d = %0d mV is ABOVE its %0d mV target -- rounded the unsafe way",
                           name, code, mv, target_mv);
                if (target_mv - mv >= lsb)
                    $fatal(1, "D: %0s boundary code %0d = %0d mV is more than one LSB (%0d mV) below %0d mV",
                           name, code, mv, lsb, target_mv);
            end
        end
    endtask

    task sample_at;
        input [7:0] code;
        output      cl;
        integer w;
        begin
            VIN_CODE = code;
            pulse_force;
            w = 0;
            while (sns_en !== 1'b1) begin
                @(negedge clk); w = w + 1;
                if (w > 8 * (SETTLE + 2) * ENV_CLKS)
                    $fatal(1, "D: sns_en never rose for code %0d", code);
            end
            while (sns_en !== 1'b0) begin
                @(negedge clk); w = w + 1;
                if (w > 8 * (SETTLE + 2) * ENV_CLKS)
                    $fatal(1, "D: sns_en stuck high for code %0d", code);
            end
            @(negedge clk);
            if (sto_q !== code)
                $fatal(1, "D: sto_q %0d != driven code %0d", sto_q, code);
            cl = vclamp;
        end
    endtask

    task check_sample;
        input [7:0]   exp_q;
        input         exp_vlow;
        input         exp_vcrit;
        input integer max_wait;
        integer w, highs, envs, goes, dones, env_at_go;
        reg [7:0] q_last_high;
        begin
            w = 0;
            while (sns_en !== 1'b1) begin
                @(negedge clk);
                w = w + 1;
                if (w > max_wait)
                    $fatal(1, "sns_en did not rise within %0d cycles", max_wait);
            end
            highs = 0; envs = 0; goes = 0; dones = 0; env_at_go = -1;
            q_last_high = sto_q;
            while (sns_en === 1'b1) begin
                highs = highs + 1;
                if (tick_env === 1'b1) envs = envs + 1;
                if (seq_go === 1'b1) begin
                    goes = goes + 1;
                    if (env_at_go < 0) env_at_go = envs;
                end
                if (sar_done === 1'b1) dones = dones + 1;
                q_last_high = sto_q;
                if (highs > (SETTLE + 1) * ENV_CLKS + 200)
                    $fatal(1, "sns_en stuck high: %0d cycles and counting", highs);
                @(negedge clk);
            end
            if (goes != 1)
                $fatal(1, "expected exactly 1 sar_go inside the sns_en window, saw %0d", goes);
            if (dones != 1)
                $fatal(1, "expected exactly 1 sar done inside the sns_en window, saw %0d", dones);
            if (env_at_go != SETTLE + 1)
                $fatal(1, "sar_go after %0d env strobes, expected %0d (SETTLE_ENV_TICKS+1: k strobes = k-1 full periods)",
                       env_at_go, SETTLE + 1);
            if (envs > SETTLE + 2)
                $fatal(1, "sns_en held across %0d env ticks -- window too long", envs);
            if (highs < SETTLE * ENV_CLKS)
                $fatal(1, "sample window only %0d cycles -- %0d full env periods of settle not honoured",
                       highs, SETTLE);
            if (highs > (SETTLE + 1) * ENV_CLKS + 60)
                $fatal(1, "sample window %0d cycles -- did not release promptly", highs);
            if (q_last_high !== exp_q)
                $fatal(1, "sto_q=%0d in the last sns_en-high cycle (exp %0d) -- gate fell BEFORE latch",
                       q_last_high, exp_q);
            if (sto_q !== exp_q)
                $fatal(1, "sto_q %0d != expected %0d after sample", sto_q, exp_q);
            if (vlow !== exp_vlow)
                $fatal(1, "vlow %b != expected %b for sample %0d", vlow, exp_vlow, exp_q);
            if (vcrit !== exp_vcrit)
                $fatal(1, "vcrit %b != expected %b for sample %0d", vcrit, exp_vcrit, exp_q);
        end
    endtask

    // ---------------- the run ----------------
    integer p;
    integer duty_x10000;

    initial begin
        /* ---------- A: SAR alone -- exact convergence, 2 clk per bit ---------- */
        tick_en = 1'b0;                          // sense_seq sees no polls: stays IDLE
        do_reset;
        sar_conv(8'd0);
        sar_conv(8'd64);
        sar_conv(8'd96);
        sar_conv(8'd200);
        sar_conv(8'd255);
        $display("A OK: SAR result == VIN_CODE exactly for 0/64/96/200/255, 16 clk each, done 1-cycle");

        /* ---------- B: cadence (16th poll, not before) + THE DUTY GATE ---------- */
        VIN_CODE = VOVCH_C;                      // healthy rail: no flags expected
        tick_en  = 1'b1;
        do_reset;
        mon_cycles = 0; mon_high = 0; mon_go = 0; mon_done = 0;
        mon_en = 1'b1;

        p = 0;
        while (p < PPS) begin
            @(negedge clk);
            if (tick_poll === 1'b1) p = p + 1;
            if (p < PPS && sns_en !== 1'b0)
                $fatal(1, "sns_en high at poll %0d -- sampled BEFORE the 16th poll", p);
        end
        // the 16th tick_poll just strobed: this is the sample
        check_sample(VOVCH_C, 1'b0, 1'b0, 6);
        $display("B1 OK: polls 1..15 gated off every cycle; sample on the 16th poll (settle=%0d env strobes = >= %0d full periods, latch-then-release)", SETTLE + 1, SETTLE);

        while (p < 2 * PPS) begin
            @(negedge clk);
            if (tick_poll === 1'b1) p = p + 1;
            if (p < 2 * PPS && sns_en !== 1'b0)
                $fatal(1, "sns_en high between samples at poll %0d", p);
        end
        check_sample(VOVCH_C, 1'b0, 1'b0, 6);
        repeat (4) @(negedge clk);
        mon_en = 1'b0;
        @(negedge clk);                          // let the monitor settle its last count

        if (mon_go != 2)
            $fatal(1, "expected exactly 2 conversions in the 32-poll run, saw %0d", mon_go);
        if (mon_done != 2)
            $fatal(1, "expected exactly 2 SAR completions in the 32-poll run, saw %0d", mon_done);
        if (mon_high == 0)
            $fatal(1, "sns_en never high across 32 polls -- no sampling happened at all");
        // THE U10 DEFERRED-READ PROPERTY (sense.c): divider duty < 2% of elapsed
        if (mon_high * 50 >= mon_cycles)
            $fatal(1, "sns_en duty %0d/%0d cycles >= 2%% -- divider not gated off between samples",
                   mon_high, mon_cycles);
        duty_x10000 = (mon_high * 10000) / mon_cycles;
        $display("B2 OK: 2 samples / 32 polls; sns_en high %0d of %0d cycles = %0d.%02d%% < 2%% (U10 deferred-read duty)",
                 mon_high, mon_cycles, duty_x10000 / 100, duty_x10000 % 100);

        /* ---------- C: force_rd immediacy + vlow/vcrit latching ---------- */
        p = 0;                                   // 3 polls into a fresh 16-poll cadence
        while (p < 3) begin
            @(negedge clk);
            if (tick_poll === 1'b1) p = p + 1;
            if (sns_en !== 1'b0)
                $fatal(1, "sns_en high mid-cadence with no force_rd (poll %0d of 16)", p);
        end
        VIN_CODE = TH_LOW - 8'd1;                // under the glow gate, above the floor
        pulse_force;
        check_sample(TH_LOW - 8'd1, 1'b1, 1'b0, 4);  // rise within 4 clk = out-of-cadence
        $display("C1 OK: force_rd at poll 3 of 16 -> immediate sample; %0d -> vlow=1 vcrit=0",
                 TH_LOW - 8'd1);

        VIN_CODE = TH_CRIT - 8'd1;               // < TH_CRIT
        pulse_force;
        check_sample(TH_CRIT - 8'd1, 1'b1, 1'b1, 4);

        VIN_CODE = TH_CRIT;                      // == TH_CRIT: NOT strictly below
        pulse_force;
        check_sample(TH_CRIT, 1'b1, 1'b0, 4);

        VIN_CODE = TH_LOW - 8'd1;                // just under the glow gate
        pulse_force;
        check_sample(TH_LOW - 8'd1, 1'b1, 1'b0, 4);

        VIN_CODE = TH_LOW;                       // == TH_LOW: NOT strictly below
        pulse_force;
        check_sample(TH_LOW, 1'b0, 1'b0, 4);

        VIN_CODE = VOVCH_C;                      // a full tank at the AEM ceiling
        pulse_force;
        check_sample(VOVCH_C, 1'b0, 1'b0, 4);
        $display("C2 OK: %0d -> vlow+vcrit; boundaries %0d/%0d not-below; VOVCH code %0d clears both",
                 TH_CRIT - 8'd1, TH_CRIT, TH_LOW, VOVCH_C);

        /* ---------- D: the thresholds are PINNED TO VOLTS ----------------------
         * C2 above proves the flags switch at the expected CODES. This proves the
         * codes mean the right MILLIVOLTS -- the part that used to be untestable,
         * because until 2026-08-19 TH_LOW/TH_CRIT were tagged "placeholder scaling"
         * and there was no volts to check against.
         * Every boundary is DISCOVERED by binary search, converted back through
         * FS_MV, and required to sit within one LSB of its board.h number ON THE
         * PROTECTIVE SIDE. That catches a wrong rounding rule even when the bench
         * and the DUT make the same mistake, which a code-vs-code check cannot. */

        // vclamp resets PESSIMISTIC (clamped) -- opposite to vlow/vcrit, because the
        // failure directions are opposite. wake_fsm can glow on a tap from the
        // STANDING latches, before the force_rd sample it triggers has landed.
        do_reset;
        @(negedge clk);
        if (vclamp !== 1'b1)
            $fatal(1, "D: vclamp resets to %b -- the guard must reset CLAMPED", vclamp);

        // --- vlow: strict-below, so the boundary is the lowest code that CLEARS it
        d_lo = 0; d_hi = 255;
        sample_at(8'd0,   d_cl); if (vlow !== 1'b1) $fatal(1, "D: code 0 is not vlow");
        sample_at(8'd255, d_cl); if (vlow !== 1'b0) $fatal(1, "D: full scale is vlow");
        while (d_hi - d_lo > 1) begin
            d_mid = (d_lo + d_hi) / 2;
            sample_at(d_mid[7:0], d_cl);
            if (vlow === 1'b0) d_hi = d_mid; else d_lo = d_mid;
        end
        check_volts("vlow ", d_hi, TH_LOW_MV, 1);
        b_low = d_hi;

        // --- vcrit: same shape, deeper floor
        d_lo = 0; d_hi = 255;
        while (d_hi - d_lo > 1) begin
            d_mid = (d_lo + d_hi) / 2;
            sample_at(d_mid[7:0], d_cl);
            if (vcrit === 1'b0) d_hi = d_mid; else d_lo = d_mid;
        end
        check_volts("vcrit", d_hi, TH_CRIT_MV, 1);
        b_crit = d_hi;

        // --- vclamp: at-or-above, so the boundary is the lowest code that SETS it
        d_lo = 0; d_hi = 255;
        sample_at(8'd0,   d_cl); if (d_cl !== 1'b0) $fatal(1, "D: code 0 is clamped");
        sample_at(8'd255, d_cl); if (d_cl !== 1'b1) $fatal(1, "D: full scale is not clamped -- guard unreachable");
        while (d_hi - d_lo > 1) begin
            d_mid = (d_lo + d_hi) / 2;
            sample_at(d_mid[7:0], d_cl);
            if (d_cl === 1'b1) d_hi = d_mid; else d_lo = d_mid;
        end
        check_volts("clamp", d_hi, TH_CLAMP_MV, 0);
        b_clamp = d_hi;

        // --- THE THREE MUST STAY IN ORDER. Nothing else checks this, and the ordering is
        // not decorative: vcrit above vlow would mean the FSM enters dormancy while the
        // glow gate still reads healthy, and the clamp below either would clamp a normal
        // glow. It is guarded because TH_CRIT_MV is the one threshold with no firmware
        // anchor (see TODO.md's bench item) -- the number most likely to be revised, and
        // revised UPWARD toward the glow floor, which is the direction that breaks this.
        if (!(b_crit < b_low && b_low < b_clamp))
            $fatal(1, "D: thresholds out of order -- vcrit %0d, vlow %0d, clamp %0d (need vcrit < vlow < clamp)",
                   b_crit, b_low, b_clamp);

        // --- and the property board.h asserts in a parenthetical: the AEM10300's own
        // VOVCH ceiling must NEVER trip the ballast guard. board.h says "(VOVCH 4.65 V
        // never trips it)"; on this scale that is a checkable fact, not a comment.
        // A full-scale chosen at VOVCH instead of 6000 mV would make the guard
        // unreachable and every other check here would still pass.
        sample_at(VOVCH_C, d_cl);
        if (d_cl !== 1'b0)
            $fatal(1, "D: a full tank at VOVCH (%0d mV, code %0d) trips the ballast guard -- board.h says it never does",
                   VOVCH_MV, VOVCH_C);
        if (vlow !== 1'b0 || vcrit !== 1'b0)
            $fatal(1, "D: a full tank at VOVCH reads low/critical");
        $display("D OK: pinned to volts (LSB %0d uV) -- vcrit %0d mV (code %0d) < vlow %0d mV (%0d) < clamp %0d mV (%0d), in order; VOVCH code %0d clears the guard",
                 (FS_MV * 1000) / 256, TH_CRIT_MV, b_crit, TH_LOW_MV, b_low,
                 TH_CLAMP_MV, b_clamp, VOVCH_C);

        $display("TB PASS: tb_sense_seq");
        $finish;
    end

endmodule
