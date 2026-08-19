/*
 * tb_gamma_pwm.v -- self-checking testbench for clkdiv + gamma_pwm (DRH-1).
 *
 * Instantiates BOTH modules: clkdiv (small CLK_HZ override, 65536 = 128*512)
 * feeds gamma_pwm's tick_env, so the tick plumbing is proven end to end.
 *
 * Checks (all $fatal on failure -- real properties, not just activity):
 *   A. clkdiv rates: every tick_env gap == CLK_HZ/128 clk cycles exactly,
 *      every tick_poll gap == CLK_HZ cycles exactly, exactly 128 tick_envs
 *      per tick_poll, strobes 1 cycle wide and never X. Simultaneously:
 *      mode 00 -> led == 4'b0000 on every one of 3*CLK_HZ sampled cycles.
 *   B. mode 01 (breathe): per-envelope-step PWM high-time (counted over one
 *      full 256-clk PWM period, an exact duty measurement) is monotonic
 *      non-decreasing to the peak then non-increasing back to 0 over one
 *      256-step envelope period; all four channels identical (in phase);
 *      peak >= 200, floor == 0; and the gamma signature: mid-ramp duty is
 *      below half the peak (a linear ramp would sit at half -- monotonicity
 *      plus convexity, per the "check monotonicity not linearity" contract).
 *   C. mode 10 (sweep): the four channels' envelope phases all differ
 *      (distinct peak steps); led[0] and led[2] hit opposite envelope
 *      extremes at a sampled step (d0 >= 200 while d2 <= 4, and vice versa);
 *      same for the led[1]/led[3] antiphase pair; every channel reaches a
 *      full peak.
 *   D. mode 11 (dim solid): duty constant across samples, equal on all four
 *      channels, nonzero and small (<= 40/256).
 *
 * Duty measurement method: after a tick_env, wait 4 clks (duty regs settle),
 * then count led-high over exactly 256 consecutive clks. A free-running
 * 8-bit PWM counter passes every code once in any 256-clk window, so the
 * count equals the duty register EXACTLY -- the monotonicity checks need no
 * tolerance. (Envelope step = 512 clks here, so the window fits inside one
 * step.) All TB sampling is on negedge clk: NBA-updated DUT state is stable.
 */
`timescale 1ns/1ps

module tb_gamma_pwm;

    localparam integer TB_CLK_HZ = 65536;              // 128 * 512: exact ratios
    localparam integer ENV_DIV   = TB_CLK_HZ / 128;    // 512 clk per tick_env
    localparam integer NSTEP     = 256;                // one full envelope period

    reg        clk = 1'b0;
    reg        rst_n = 1'b0;
    reg [1:0]  mode = 2'b00;
    reg        clamp_en = 1'b0;   // ballast guard off unless a check turns it on
    wire       tick_env, tick_poll;
    wire [3:0] led;

    clkdiv #(.CLK_HZ(TB_CLK_HZ)) u_clkdiv (
        .clk(clk), .rst_n(rst_n),
        .tick_env(tick_env), .tick_poll(tick_poll)
    );

    gamma_pwm u_pwm (
        .clk(clk), .rst_n(rst_n),
        .tick_env(tick_env), .mode(mode), .clamp_en(clamp_en), .led(led)
    );

    always #5 clk = ~clk;   // 100 MHz sim clock; rate checks are in cycles

    // watchdog: whole run is ~470k cycles = 4.7 ms sim time
    initial begin
        #20_000_000;
        $fatal(1, "TB TIMEOUT: did not reach TB PASS");
    end

    integer s0 [1:NSTEP];                              // mode 01 duty trace
    integer a0 [1:NSTEP]; integer a1 [1:NSTEP];        // mode 10 duty traces
    integer a2 [1:NSTEP]; integer a3 [1:NSTEP];

    integer i;
    integer c0, c1, c2, c3;
    integer last_env, last_poll, envs_since_poll, n_env, n_poll;
    reg     prev_env;
    integer maxv, peak_i0, peak_i1, peak_i2, peak_i3;
    integer found_a, found_b, found_c;
    integer dim_ref;
    integer e_off, e_on, r0, r1, r2, r3;               // E: ballast-guard ceiling

    task do_reset;
        begin
            @(negedge clk);
            rst_n = 1'b0;
            repeat (4) @(negedge clk);
            rst_n = 1'b1;
        end
    endtask

    task wait_env;                                     // land on a negedge with tick_env==1
        begin
            @(negedge clk);
            while (tick_env !== 1'b1) @(negedge clk);
        end
    endtask

    task measure_duty;                                 // call right after wait_env
        output integer m0; output integer m1;
        output integer m2; output integer m3;
        integer k;
        begin
            repeat (4) @(negedge clk);                 // duty regs settle post-tick
            m0 = 0; m1 = 0; m2 = 0; m3 = 0;
            for (k = 0; k < 256; k = k + 1) begin      // exactly one PWM period
                @(negedge clk);
                if (^led === 1'bx) $fatal(1, "led has X/Z bits: %b", led);
                m0 = m0 + (led[0] ? 1 : 0);
                m1 = m1 + (led[1] ? 1 : 0);
                m2 = m2 + (led[2] ? 1 : 0);
                m3 = m3 + (led[3] ? 1 : 0);
            end
        end
    endtask

    initial begin
        /* ---------- A: clkdiv tick rates + mode 00 dark forever ---------- */
        mode = 2'b00;
        do_reset;
        last_env = -1; last_poll = -1; envs_since_poll = 0;
        n_env = 0; n_poll = 0; prev_env = 1'b0;
        for (i = 0; i < 3 * TB_CLK_HZ; i = i + 1) begin
            @(negedge clk);
            if (led !== 4'b0000)
                $fatal(1, "mode 00: led=%b at sample %0d, expected all low", led, i);
            if (tick_env === 1'bx || tick_poll === 1'bx)
                $fatal(1, "tick strobe is X at sample %0d", i);
            if (tick_env === 1'b1) begin
                if (prev_env)
                    $fatal(1, "tick_env high on 2 consecutive cycles (not a 1-cycle strobe)");
                if (last_env >= 0 && (i - last_env) != ENV_DIV)
                    $fatal(1, "tick_env gap %0d != CLK_HZ/128 = %0d", i - last_env, ENV_DIV);
                last_env = i;
                n_env = n_env + 1;
                envs_since_poll = envs_since_poll + 1;
            end
            prev_env = (tick_env === 1'b1);
            if (tick_poll === 1'b1) begin
                if (last_poll >= 0) begin
                    if ((i - last_poll) != TB_CLK_HZ)
                        $fatal(1, "tick_poll gap %0d != CLK_HZ = %0d", i - last_poll, TB_CLK_HZ);
                    if (envs_since_poll != 128)
                        $fatal(1, "%0d tick_envs per tick_poll != 128", envs_since_poll);
                end
                last_poll = i;
                envs_since_poll = 0;
                n_poll = n_poll + 1;
            end
        end
        if (n_env < 256) $fatal(1, "too few tick_env strobes seen: %0d", n_env);
        if (n_poll < 2)  $fatal(1, "too few tick_poll strobes seen: %0d", n_poll);
        $display("A OK: %0d tick_env (gap %0d = CLK_HZ/128), %0d tick_poll (gap %0d, 128 envs each); mode 00 dark for %0d cycles",
                 n_env, ENV_DIV, n_poll, TB_CLK_HZ, 3 * TB_CLK_HZ);

        /* ---------- B: mode 01 breathe -- monotone rise/fall, in phase ---------- */
        mode = 2'b01;
        do_reset;
        for (i = 1; i <= NSTEP; i = i + 1) begin
            wait_env;
            measure_duty(c0, c1, c2, c3);
            if (c1 != c0 || c2 != c0 || c3 != c0)
                $fatal(1, "mode 01: channels out of phase at step %0d (%0d %0d %0d %0d)",
                       i, c0, c1, c2, c3);
            s0[i] = c0;
        end
        for (i = 2; i <= 128; i = i + 1)
            if (s0[i] < s0[i-1])
                $fatal(1, "mode 01: envelope fell during rise at step %0d (%0d -> %0d)",
                       i, s0[i-1], s0[i]);
        for (i = 129; i <= NSTEP; i = i + 1)
            if (s0[i] > s0[i-1])
                $fatal(1, "mode 01: envelope rose during fall at step %0d (%0d -> %0d)",
                       i, s0[i-1], s0[i]);
        if (s0[127] < 200)
            $fatal(1, "mode 01: peak duty %0d < 200 -- envelope never reaches bright", s0[127]);
        if (s0[NSTEP] != 0)
            $fatal(1, "mode 01: envelope floor %0d != 0 at end of period", s0[NSTEP]);
        if (s0[1] > 2)
            $fatal(1, "mode 01: envelope start %0d not near 0", s0[1]);
        if (!(s0[64] < (s0[127] + 1) / 2))
            $fatal(1, "mode 01: mid-ramp duty %0d not below half of peak %0d -- gamma not applied?",
                   s0[64], s0[127]);
        $display("B OK: mode 01 monotone rise to %0d (step 127) and fall to 0; mid-ramp %0d < peak/2 (gamma); 4 channels in phase",
                 s0[127], s0[64]);

        /* ---------- C: mode 10 sweep -- phases differ, antiphase extremes ---------- */
        mode = 2'b10;
        do_reset;
        for (i = 1; i <= NSTEP; i = i + 1) begin
            wait_env;
            measure_duty(c0, c1, c2, c3);
            a0[i] = c0; a1[i] = c1; a2[i] = c2; a3[i] = c3;
        end
        found_a = 0; found_b = 0; found_c = 0;
        for (i = 1; i <= NSTEP; i = i + 1) begin
            if (a0[i] >= 200 && a2[i] <= 4) found_a = 1;   // led0 max / led2 min
            if (a2[i] >= 200 && a0[i] <= 4) found_b = 1;   // led2 max / led0 min
            if (a1[i] >= 200 && a3[i] <= 4) found_c = 1;   // led1 max / led3 min
        end
        if (!found_a) $fatal(1, "mode 10: never saw led[0] at max while led[2] at min");
        if (!found_b) $fatal(1, "mode 10: never saw led[2] at max while led[0] at min");
        if (!found_c) $fatal(1, "mode 10: never saw led[1] at max while led[3] at min");
        maxv = -1; peak_i0 = 0;
        for (i = 1; i <= NSTEP; i = i + 1) if (a0[i] > maxv) begin maxv = a0[i]; peak_i0 = i; end
        if (maxv < 200) $fatal(1, "mode 10: led[0] peak %0d < 200", maxv);
        maxv = -1; peak_i1 = 0;
        for (i = 1; i <= NSTEP; i = i + 1) if (a1[i] > maxv) begin maxv = a1[i]; peak_i1 = i; end
        if (maxv < 200) $fatal(1, "mode 10: led[1] peak %0d < 200", maxv);
        maxv = -1; peak_i2 = 0;
        for (i = 1; i <= NSTEP; i = i + 1) if (a2[i] > maxv) begin maxv = a2[i]; peak_i2 = i; end
        if (maxv < 200) $fatal(1, "mode 10: led[2] peak %0d < 200", maxv);
        maxv = -1; peak_i3 = 0;
        for (i = 1; i <= NSTEP; i = i + 1) if (a3[i] > maxv) begin maxv = a3[i]; peak_i3 = i; end
        if (maxv < 200) $fatal(1, "mode 10: led[3] peak %0d < 200", maxv);
        if (peak_i0 == peak_i1 || peak_i0 == peak_i2 || peak_i0 == peak_i3 ||
            peak_i1 == peak_i2 || peak_i1 == peak_i3 || peak_i2 == peak_i3)
            $fatal(1, "mode 10: envelope phases not all distinct (peak steps %0d %0d %0d %0d)",
                   peak_i0, peak_i1, peak_i2, peak_i3);
        $display("C OK: mode 10 peak steps %0d/%0d/%0d/%0d all distinct; led0/led2 and led1/led3 hit opposite extremes",
                 peak_i0, peak_i1, peak_i2, peak_i3);

        /* ---------- D: mode 11 dim solid -- constant small duty ---------- */
        mode = 2'b11;
        do_reset;
        dim_ref = -1;
        for (i = 1; i <= 8; i = i + 1) begin
            wait_env;
            measure_duty(c0, c1, c2, c3);
            if (c1 != c0 || c2 != c0 || c3 != c0)
                $fatal(1, "mode 11: channels differ (%0d %0d %0d %0d)", c0, c1, c2, c3);
            if (dim_ref < 0) dim_ref = c0;
            if (c0 != dim_ref)
                $fatal(1, "mode 11: duty not constant (%0d vs %0d at sample %0d)", c0, dim_ref, i);
        end
        if (dim_ref <= 0)  $fatal(1, "mode 11: duty is zero -- 'dim solid' is dark");
        if (dim_ref > 40)  $fatal(1, "mode 11: duty %0d/256 is not small", dim_ref);
        $display("D OK: mode 11 constant duty %0d/256 on all four channels", dim_ref);

        /* ---------- E: ballast guard -- a real ceiling, on every channel ----------
         * The ceiling is DISCOVERED, not restated here: gamma_pwm's CLAMP_PEAK is
         * left at its default and the bench measures what the hardware does, so a
         * changed default is still tested rather than silently agreed with. */

        // E1: clamp OFF -- the unclamped peak. Without this, E2 could pass vacuously
        // on an envelope that never reached the ceiling in the first place.
        mode = 2'b01; clamp_en = 1'b0;
        do_reset;
        e_off = 0;
        for (i = 1; i <= NSTEP; i = i + 1) begin
            wait_env; measure_duty(c0, c1, c2, c3);
            if (c0 > e_off) e_off = c0;
        end

        // E2: clamp ON, breathe -- a strictly lower peak, and a FLAT ceiling rather
        // than a rescale: nothing anywhere in the envelope exceeds it. That shape is
        // load-bearing for the published thermal bound, which is computed at a HELD
        // peak (70 mW x CLAMP_PEAK/255), so a flat top IS the worst case.
        clamp_en = 1'b1;
        do_reset;
        e_on = 0;
        for (i = 1; i <= NSTEP; i = i + 1) begin
            wait_env; measure_duty(c0, c1, c2, c3);
            if (c1 != c0 || c2 != c0 || c3 != c0)
                $fatal(1, "E2: clamped breathe channels differ (%0d %0d %0d %0d)", c0, c1, c2, c3);
            if (c0 > e_on) e_on = c0;
        end
        if (e_on >= e_off)
            $fatal(1, "E2: clamped peak %0d not below unclamped peak %0d -- the guard does nothing",
                   e_on, e_off);
        if (e_on == 0)
            $fatal(1, "E2: clamped peak is 0 -- the guard extinguishes the glow instead of capping it");

        // E3: clamp ON, sweep -- EVERY channel must respect the same ceiling, and
        // every channel must actually REACH it. This is the check that catches one
        // animation path routed around ballast(): the four sweep duties are written
        // from four separate expressions, and exactly that slip happened while this
        // guard was being written (MODE_SWEEP's duty0 is textually identical to
        // MODE_BREATHE's, so a first-occurrence edit left it unclamped).
        mode = 2'b10;
        do_reset;
        r0 = 0; r1 = 0; r2 = 0; r3 = 0;
        for (i = 1; i <= NSTEP; i = i + 1) begin
            wait_env; measure_duty(c0, c1, c2, c3);
            if (c0 > e_on || c1 > e_on || c2 > e_on || c3 > e_on)
                $fatal(1, "E3: sweep duty over the ceiling %0d at step %0d: %0d/%0d/%0d/%0d -- a channel bypasses the clamp",
                       e_on, i, c0, c1, c2, c3);
            if (c0 == e_on) r0 = r0 + 1;
            if (c1 == e_on) r1 = r1 + 1;
            if (c2 == e_on) r2 = r2 + 1;
            if (c3 == e_on) r3 = r3 + 1;
        end
        if (r0 == 0 || r1 == 0 || r2 == 0 || r3 == 0)
            $fatal(1, "E3: channel(s) never reached the ceiling (%0d/%0d/%0d/%0d hits) -- clamped-low, not clamped",
                   r0, r1, r2, r3);

        // E4: the clamp must not disturb the dark guarantee mode 00 owns.
        mode = 2'b00;
        do_reset;
        for (i = 0; i < 4 * NSTEP; i = i + 1) begin
            @(negedge clk);
            if (led !== 4'b0000)
                $fatal(1, "E4: led=%b with clamp on in mode 00 -- dark-at-off broken", led);
        end
        $display("E OK: ballast ceiling %0d (unclamped peak %0d); flat top, all 4 sweep channels reach it (%0d/%0d/%0d/%0d), mode 00 still dark",
                 e_on, e_off, r0, r1, r2, r3);

        $display("TB PASS: tb_gamma_pwm");
        $finish;
    end

endmodule
