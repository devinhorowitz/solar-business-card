// ---------------------------------------------------------------------------
// tb_top.v -- self-checking integration TB for drh1_top (+ a TT-wrapper
//             smoke path), the DRH-1 digital core end to end.
//
// This is the firmware/main.c day-in-the-life, replayed against the silicon:
// power-up -> accel config over I2C (adxl367_init_tap) -> tap -> rail-gated
// glow -> supercap collapses -> dormancy with charge tell -> taps dead ->
// rail recovers -> taps live again. The ADXL367 is tb/i2c_slave_model.v at
// 7'h1D; the SAR's analog half is a behavioural comparator against VIN_CODE
// (cmp_in = VIN_CODE > dac_code, SPEC's strictly-greater convention, which
// sar_ctrl's T-1 DAC drive turns into EXACT convergence -- asserted here).
//
// Checks REAL properties, $fatal on any failure, "TB PASS: tb_top" only if
// every one holds:
//   [1] reset -> init: the slave sees >= 5 register writes addressed to
//       0x1D, and the FIRST is {SOFT_RESET 0x1F <- 0x52}, init_seq ROM
//       entry 0; LEDs dark and mode 00 until then (dark at reset).
//   [2] healthy rail (VIN_OK = VOVCH) -> tap on int1 -> mode 01 within a few
//       clk, the tap-forced sample runs and latches sto_q == VIN_CODE
//       exactly, and ALL FOUR led lines show PWM edges inside the glow
//       window (> 10 rising edges each); glow self-terminates (mode 00,
//       LEDs solid low) after GLOW_POLLS.
//   [3] VIN_CODE dropped below TH_CRIT -> the next PERIODIC sample
//       latches it (sto_q == 30) and brownout rises; an NFC field pulse
//       during the wait proves nfc_en rises with fd_n low and has expired
//       (NFC_HOLD_POLLS) by dormancy time -- the FD path is state-independent.
//   [4] tap in DORMANT: ZERO led edges over a 2-poll window, brownout stays
//       up, and the tap forces NO sample (sample count unchanged) -- taps
//       are ignored, not deferred.
//   [5] VIN_CODE raised -> next periodic sample -> brownout released, and a
//       fresh tap glows again (> 10 edges per led, mode 01).
//   [5b] vcrit latches MID-ANIMATION (the one path invariant [8] cannot see
//       otherwise, since every other dormancy entry happens from idle with
//       the LEDs already dark): VIN_CODE collapses BEFORE a tap, so the
//       standing vlow latch still says healthy, the glow fires, and the
//       tap-FORCED sample itself latches vcrit while the breathe animation
//       is live. Asserts mode 01 held right up to the cut, the LEDs are
//       dark at the FIRST negedge with brownout high -- i.e. from the SAME
//       clk edge brownout rises, which only gamma_pwm's combinational
//       mode-off can provide (the duty regs clear one clk later) -- and the
//       animation never resumes on its own (zero led edges, mode 00,
//       brownout held, over 2 polls). The tap is placed at a measured
//       envelope phase so the cut lands at duty ~144/256: if the
//       combinational off is reverted, the one-clk drive is a REAL lit
//       cycle and this scenario (and [8]) must fail.
//   [6] sns_en duty over the WHOLE run < 2% (the U10 gate rule: the divider
//       only exists while a conversion needs it), with >= 4 samples seen.
//   [7] TT wrapper smoke path (its own bus + slave): the identical init
//       write set arrives THROUGH the pad model (>= 5 writes, first is
//       0x1F <- 0x52), uio_oe[7:1] is constantly driven / uio_out[0]
//       constantly low (open-drain SDA), and its SCL idles high.
//   [8] standing invariant, every clk: brownout high -> all four LEDs low
//       (dormancy means DARK; a single lit clk fails the run).
//
// Scaling: drh1_top's CLK_HZ pass-through runs clkdiv at 32768 "Hz", so one
// tick_poll = 32768 clk and one tick_env = 256 clk -- the exact 128:1
// env:poll ratio of the real part at ~1/30 the cycle count. The TT wrapper
// core keeps the default 1 MHz scaling (its tick-driven paths are not under
// test; its I2C engine is tick-independent).
// ---------------------------------------------------------------------------

`timescale 1ns/1ps

module tb_top;

    localparam integer CLK_HZ_SIM = 32768;        // scaled core clock rate
    localparam integer POLL_CLKS  = CLK_HZ_SIM;   // clk per tick_poll
    localparam integer CLK_NS     = 10;

    localparam [6:0] ACCEL_ADDR = 7'h1D;          // ADXL367, ASEL grounded
    /* THE ANALOG CONTRACT, again. This bench drives a behavioural comparator, so its
     * rail codes have to mean the same volts sense_seq's thresholds do -- derived
     * here from millivolts rather than typed, so a scale change carries the scenarios
     * with it instead of silently landing them on the wrong side of a threshold.
     * NOT hypothetical: pinning the thresholds to volts on 2026-08-19 moved TH_CLAMP
     * from code 181 to 221 and left the old VIN_OK = 200 BELOW it, so the "high rail"
     * scenario quietly stopped being a high rail. [9] failed and said so. */
    localparam integer FS_MV       = 6000;   // = sense_seq.FS_MV
    localparam integer VIN_OK_MV   = 4650;   // AEM10300 VOVCH: the fullest a card gets
    localparam integer VIN_HIGH_MV = 5500;   // the supercap RATING -- bench-supply abuse,
                                             //   the only place the ballast guard fires
    localparam integer VIN_DEAD_MV =  700;   // far below the 2000 mV dormancy floor

    localparam [7:0] VIN_OK   = (VIN_OK_MV   * 256) / FS_MV;   // 198, below TH_CLAMP 221
    localparam [7:0] VIN_HIGH = (VIN_HIGH_MV * 256) / FS_MV;   // 234, above it
    localparam [7:0] VIN_DEAD = (VIN_DEAD_MV * 256) / FS_MV;   // 29,  below TH_CRIT 86

    /* ---- DUT: drh1_top on its own I2C bus -------------------------------- */
    reg         clk, rst_n;
    reg         int1, int2, fd_n;
    reg  [7:0]  vin_code;

    wire [3:0]  led;
    wire        scl, sda;
    wire        nfc_en, sns_en, brownout;
    wire [7:0]  dac_code, dbg_sto;
    wire [1:0]  dbg_mode;

    pullup pu_sda (sda);                          // the board's 4.7k pull-ups

    // Behavioural comparator (the analog stub): 1 when Vin > DAC(dac_code).
    wire cmp_in = (vin_code > dac_code);

    drh1_top #(.CLK_HZ(CLK_HZ_SIM)) dut (
        .clk(clk), .rst_n(rst_n),
        .led(led),
        .sda(sda), .scl(scl),
        .int1(int1), .int2(int2), .fd_n(fd_n),
        .nfc_en(nfc_en), .sns_en(sns_en), .brownout(brownout),
        .cmp_in(cmp_in), .dac_code(dac_code),
        .dbg_sto(dbg_sto), .dbg_mode(dbg_mode)
    );

    i2c_slave_model #(.DEV_ADDR(ACCEL_ADDR)) slave (
        .scl(scl), .sda(sda)
    );

    /* ---- TT wrapper smoke path: own pad-model bus, own slave ------------- */
    reg  [7:0] tt_ui_in;
    wire [7:0] tt_uo_out, tt_uio_out, tt_uio_oe;
    wire       tt_sda;

    pullup pu_tt_sda (tt_sda);
    // The chip-side pad driver: TT drives the uio pad when oe=1.
    assign tt_sda = (tt_uio_oe[0] === 1'b1 && tt_uio_out[0] === 1'b0)
                    ? 1'b0 : 1'bz;
    // uio_in reflects the resolved pad level (what real TT harness pins do).
    wire [7:0] tt_uio_in = {7'b0000000, tt_sda};

    tt_um_drh_solarglow tt (
        .ui_in(tt_ui_in), .uo_out(tt_uo_out),
        .uio_in(tt_uio_in), .uio_out(tt_uio_out), .uio_oe(tt_uio_oe),
        .ena(1'b1), .clk(clk), .rst_n(rst_n)
    );

    i2c_slave_model #(.DEV_ADDR(ACCEL_ADDR)) tt_slave (
        .scl(tt_uo_out[7]), .sda(tt_sda)
    );

    /* ---- clock ------------------------------------------------------------ */
    initial clk = 1'b0;
    always #(CLK_NS/2) clk = ~clk;

    /* ---- LED edge counters (window-gated) --------------------------------- */
    reg     win_en;
    integer ec0, ec1, ec2, ec3;

    always @(posedge led[0]) if (win_en) ec0 = ec0 + 1;
    always @(posedge led[1]) if (win_en) ec1 = ec1 + 1;
    always @(posedge led[2]) if (win_en) ec2 = ec2 + 1;
    always @(posedge led[3]) if (win_en) ec3 = ec3 + 1;

    task clr_edges;
        begin ec0 = 0; ec1 = 0; ec2 = 0; ec3 = 0; end
    endtask

    /* ---- sns_en duty + sample bookkeeping (whole run) ---------------------- */
    integer sns_on, sns_total, samples;

    always @(posedge clk) if (rst_n === 1'b1) begin
        sns_total = sns_total + 1;
        if (sns_en === 1'b1) sns_on = sns_on + 1;
    end
    always @(posedge sns_en) samples = samples + 1;

    /* ---- first-write capture, both slaves ---------------------------------- */
    reg       gf_main, gf_tt;
    reg [7:0] fw_reg_main, fw_val_main, fw_reg_tt, fw_val_tt;

    always @(slave.wr_count)
        if (!gf_main && slave.wr_count == 1) begin
            gf_main     = 1'b1;
            fw_reg_main = slave.last_wr_reg;
            fw_val_main = slave.last_wr_val;
        end
    always @(tt_slave.wr_count)
        if (!gf_tt && tt_slave.wr_count == 1) begin
            gf_tt     = 1'b1;
            fw_reg_tt = tt_slave.last_wr_reg;
            fw_val_tt = tt_slave.last_wr_val;
        end

    /* ---- standing invariants, every clk ------------------------------------ */
    always @(posedge clk) if (rst_n === 1'b1) begin
        // [8] dormancy means DARK
        if (brownout === 1'b1 && led !== 4'b0000)
            $fatal(1, "LED %b lit while brownout high (dormancy must be dark)", led);
        // [7] uio_oe constant except the sda bit; SDA pad only ever drives low
        if (tt_uio_oe[7:1] !== 7'b1111111)
            $fatal(1, "tt uio_oe[7:1]=%b, must be constantly driven", tt_uio_oe[7:1]);
        if (tt_uio_out[0] !== 1'b0)
            $fatal(1, "tt uio_out[0]=%b, open-drain SDA must only drive low",
                   tt_uio_out[0]);
    end

    /* ---- helpers ------------------------------------------------------------ */
    integer k;   // shared wait counter (single sequential stimulus thread)
    integer pk_hi, pk_mid;   // [9] ballast guard: peak duty at two rails

    task do_tap;                              // one crisp int1 rising edge
        begin
            @(negedge clk); int1 = 1'b1;
            repeat (8) @(negedge clk);
            int1 = 1'b0;
            repeat (2) @(negedge clk);
        end
    endtask

    /* max PWM high-time per 256-clk period over a glow window, used by [9]. The
     * free-running 8-bit PWM counter passes every code once per 256 clks, so a
     * window that does not straddle an envelope step counts the duty register
     * exactly; here the env period IS 256 clks (CLK_HZ_SIM/128), so a window can
     * blend two adjacent steps -- which bounds the reading between them and leaves
     * the clamped/unclamped comparison sound without needing a tolerance. */
    task glow_peak_duty;
        output integer pk;
        integer w, n, cnt;
        begin
            do_tap;
            pk = 0;
            for (n = 0; n < (5 * POLL_CLKS) / 512; n = n + 1) begin
                cnt = 0;
                for (w = 0; w < 256; w = w + 1) begin
                    @(negedge clk);
                    if (led[0] === 1'bx) $fatal(1, "[9] led[0] is X during the glow");
                    if (led[0] === 1'b1) cnt = cnt + 1;
                end
                if (cnt > pk) pk = cnt;
            end
        end
    endtask

    task check_edges_gt (input integer min);
        begin
            if (!(ec0 > min && ec1 > min && ec2 > min && ec3 > min))
                $fatal(1, "LED edges %0d/%0d/%0d/%0d, need > %0d each",
                       ec0, ec1, ec2, ec3, min);
        end
    endtask

    /* ---- global watchdog ---------------------------------------------------- */
    initial begin
        #60000000;                            // 60 ms >> the whole scenario
        $fatal(1, "global TB watchdog expired");
    end

    /* ---- scenario ------------------------------------------------------------ */
    integer s_before;

    initial begin
        // bookkeeping init
        win_en  = 1'b0;  clr_edges;
        sns_on  = 0; sns_total = 0; samples = 0;
        gf_main = 1'b0; gf_tt = 1'b0;
        fw_reg_main = 8'h00; fw_val_main = 8'h00;
        fw_reg_tt   = 8'h00; fw_val_tt   = 8'h00;

        // pins
        int1 = 1'b0; int2 = 1'b0; fd_n = 1'b1;
        vin_code = VIN_OK;
        tt_ui_in = 8'b0000_0100;              // fd_n=1, int1/int2/cmp_in=0

        rst_n = 1'b0;
        repeat (8) @(negedge clk);
        rst_n = 1'b1;

        /* [1] init: the boot kick runs init_seq's ROM into the slave */
        k = 0;
        while (dut.u_init.done_all !== 1'b1 && k < 2 * POLL_CLKS) begin
            @(posedge clk); k = k + 1;
        end
        if (dut.u_init.done_all !== 1'b1)
            $fatal(1, "init_seq did not complete (fail=%b)", dut.u_init.fail);
        if (slave.wr_count < 5)
            $fatal(1, "slave saw %0d init writes, need >= 5", slave.wr_count);
        if (fw_reg_main !== 8'h1F || fw_val_main !== 8'h52)
            $fatal(1, "first init write {%h<=%h}, expected SOFT_RESET {1f<=52}",
                   fw_reg_main, fw_val_main);
        if (led !== 4'b0000 || dbg_mode !== 2'b00 || brownout !== 1'b0)
            $fatal(1, "not dark/idle after init (led=%b mode=%b brownout=%b)",
                   led, dbg_mode, brownout);
        $display("[1] init OK: %0d writes, first = SOFT_RESET", slave.wr_count);

        /* [2] healthy tap -> glow: mode 01, exact sample, edges on all four */
        clr_edges; win_en = 1'b1;
        do_tap;
        repeat (4) @(posedge clk);
        if (dbg_mode !== 2'b01)
            $fatal(1, "tap did not start breathe (mode=%b)", dbg_mode);
        // the tap-forced sample: arm, finish, latch VIN_CODE exactly
        k = 0;
        while (sns_en !== 1'b1 && k < POLL_CLKS) begin @(posedge clk); k = k + 1; end
        if (sns_en !== 1'b1) $fatal(1, "tap did not force a sense sample");
        k = 0;
        while (sns_en !== 1'b0 && k < POLL_CLKS) begin @(posedge clk); k = k + 1; end
        if (sns_en !== 1'b0) $fatal(1, "forced sample never finished");
        if (dbg_sto !== VIN_OK)
            $fatal(1, "sto_q=%0d after healthy sample, expected %0d (exact SAR)",
                   dbg_sto, VIN_OK);
        // ride the glow window (well inside GLOW_POLLS = 4)
        repeat (3 * POLL_CLKS / 2) @(posedge clk);
        win_en = 1'b0;
        check_edges_gt(10);
        // glow self-terminates
        k = 0;
        while (dbg_mode !== 2'b00 && k < 6 * POLL_CLKS) begin @(posedge clk); k = k + 1; end
        if (dbg_mode !== 2'b00) $fatal(1, "glow did not end after GLOW_POLLS");
        repeat (8) @(posedge clk);
        if (led !== 4'b0000) $fatal(1, "LEDs not solid low after glow (%b)", led);
        $display("[2] glow OK: edges %0d/%0d/%0d/%0d, sto=%0d",
                 ec0, ec1, ec2, ec3, dbg_sto);

        /* [3] rail collapse -> dormancy on the next periodic sample;
         *     NFC field pulse rides the same wait (state-independent path) */
        vin_code = VIN_DEAD;
        fd_n = 1'b0;                           // reader field arrives
        repeat (4) @(posedge clk);
        if (nfc_en !== 1'b1) $fatal(1, "nfc_en did not rise with fd_n low");
        repeat (16) @(posedge clk);
        fd_n = 1'b1;                           // field leaves; hold starts
        k = 0;
        while (brownout !== 1'b1 && k < 20 * POLL_CLKS) begin @(posedge clk); k = k + 1; end
        if (brownout !== 1'b1)
            $fatal(1, "brownout never rose after VIN dropped below TH_CRIT");
        if (dbg_sto !== VIN_DEAD)
            $fatal(1, "sto_q=%0d in dormancy, expected %0d", dbg_sto, VIN_DEAD);
        if (dbg_mode !== 2'b00) $fatal(1, "mode=%b in dormancy", dbg_mode);
        if (nfc_en !== 1'b0)
            $fatal(1, "nfc_en still up long after NFC_HOLD_POLLS expired");
        $display("[3] dormancy OK: brownout up, sto=%0d, NFC hold expired", dbg_sto);

        /* [4] tap in DORMANT: ignored -- zero edges, no forced sample */
        clr_edges; win_en = 1'b1;
        s_before = samples;
        do_tap;
        repeat (2 * POLL_CLKS) @(posedge clk);
        win_en = 1'b0;
        if (ec0 !== 0 || ec1 !== 0 || ec2 !== 0 || ec3 !== 0)
            $fatal(1, "LED edges %0d/%0d/%0d/%0d during dormancy, expected 0",
                   ec0, ec1, ec2, ec3);
        if (brownout !== 1'b1) $fatal(1, "brownout dropped while VIN still dead");
        if (samples !== s_before)
            $fatal(1, "a dormant tap forced a sample (taps must be IGNORED)");
        $display("[4] dormant tap OK: dark, no sample");

        /* [5] recovery: next periodic sample releases brownout; tap glows */
        vin_code = VIN_OK;
        k = 0;
        while (brownout !== 1'b0 && k < 20 * POLL_CLKS) begin @(posedge clk); k = k + 1; end
        if (brownout !== 1'b0)
            $fatal(1, "brownout never released after VIN recovered");
        if (dbg_sto !== VIN_OK)
            $fatal(1, "sto_q=%0d after recovery sample, expected %0d",
                   dbg_sto, VIN_OK);
        clr_edges; win_en = 1'b1;
        do_tap;
        repeat (4) @(posedge clk);
        if (dbg_mode !== 2'b01)
            $fatal(1, "post-recovery tap did not glow (mode=%b)", dbg_mode);
        repeat (3 * POLL_CLKS / 2) @(posedge clk);
        win_en = 1'b0;
        check_edges_gt(10);
        $display("[5] recovery OK: edges %0d/%0d/%0d/%0d", ec0, ec1, ec2, ec3);

        /* [5b] vcrit cuts a LIVE glow: dark from the same edge brownout rises */
        // let [5]'s glow run out back to idle (standing latches: healthy)
        k = 0;
        while (dbg_mode !== 2'b00 && k < 6 * POLL_CLKS) begin @(posedge clk); k = k + 1; end
        if (dbg_mode !== 2'b00) $fatal(1, "[5b] setup: [5] glow did not end");
        // place the tap at a measured envelope phase: the forced sample takes
        // ~6 env ticks, so a tap at phase 90 puts the vcrit cut at phase ~96
        // -> breathe duty gamma(tri255(96)) = 144/256. pwm_cnt is env-aligned
        // (both count from the same rst_n at 256 clk/env here), so the cut
        // cycle sits ~20 counts into the PWM period: a reverted combinational
        // mode-off WOULD light the LEDs on that one clk. No luck involved.
        @(negedge clk);
        while (dut.u_pwm.phase !== 8'd90) @(negedge clk);
        vin_code = VIN_DEAD;                   // rail collapses; vlow latch stale-healthy
        do_tap;
        repeat (4) @(posedge clk);
        if (dbg_mode !== 2'b01)
            $fatal(1, "[5b] tap on stale-healthy latch did not glow (mode=%b)", dbg_mode);
        // ride the live animation up to the cut; mode 01 must hold throughout
        k = 0;
        @(negedge clk);
        while (brownout !== 1'b1 && k < 2 * POLL_CLKS) begin
            if (dbg_mode !== 2'b01)
                $fatal(1, "[5b] animation lost (mode=%b) before vcrit latched", dbg_mode);
            @(negedge clk); k = k + 1;
        end
        if (brownout !== 1'b1)
            $fatal(1, "[5b] forced sample did not latch vcrit mid-glow");
        // FIRST negedge with brownout high == the same clk edge it rose on:
        // the duty regs still hold the breathe value for this one cycle, so
        // only the combinational mode-off can make this pass (finding 3).
        if (led !== 4'b0000)
            $fatal(1, "[5b] led=%b on the clk edge brownout rose -- one-clk drive while charging disabled", led);
        if (dbg_mode !== 2'b00)
            $fatal(1, "[5b] mode=%b on the brownout edge, expected 00", dbg_mode);
        if (dbg_sto !== VIN_DEAD)
            $fatal(1, "[5b] sto_q=%0d at the cut, expected %0d", dbg_sto, VIN_DEAD);
        // the animation must never resume on its own
        clr_edges; win_en = 1'b1;
        repeat (2 * POLL_CLKS) @(posedge clk);
        win_en = 1'b0;
        if (ec0 !== 0 || ec1 !== 0 || ec2 !== 0 || ec3 !== 0)
            $fatal(1, "[5b] led edges %0d/%0d/%0d/%0d after the mid-glow cut, expected 0",
                   ec0, ec1, ec2, ec3);
        if (brownout !== 1'b1) $fatal(1, "[5b] brownout dropped while VIN still dead");
        if (dbg_mode !== 2'b00) $fatal(1, "[5b] animation resumed on its own (mode=%b)", dbg_mode);
        $display("[5b] mid-glow vcrit OK: dark on the brownout edge, no resume");
        // recover so [6]/[7] see the run-out state the old scenario ended in
        vin_code = VIN_OK;
        k = 0;
        while (brownout !== 1'b0 && k < 20 * POLL_CLKS) begin @(posedge clk); k = k + 1; end
        if (brownout !== 1'b0)
            $fatal(1, "[5b] brownout never released after recovery");

        /* [9] BALLAST GUARD, end to end: sense_seq measures, gamma_pwm acts, and
         * the only thing that can prove they are CONNECTED is a difference visible
         * at the LED pins. The unit benches each pass with .clamp_en() left off the
         * instantiation entirely; this one does not.
         * Two rails, one tap each, nothing else changed. VIN_HIGH is the 5.5 V abuse
         * corner and above the clamp threshold; VIN_OK is the AEM's own VOVCH ceiling,
         * the fullest a real card ever gets, which must still glow at full amplitude. Both are latched
         * by a periodic sample BEFORE the tap, because the glow decision and the
         * clamp both read the standing latch (see sense_seq's design note); the
         * force_rd the tap issues gates the NEXT event, not this one. */
        vin_code = VIN_HIGH;
        k = 0;
        while (dbg_sto !== VIN_HIGH && k < 20 * POLL_CLKS) begin @(posedge clk); k = k + 1; end
        if (dbg_sto !== VIN_HIGH) $fatal(1, "[9] sto never latched VIN_HIGH");
        glow_peak_duty(pk_hi);

        k = 0;
        while (dbg_mode !== 2'b00 && k < 8 * POLL_CLKS) begin @(posedge clk); k = k + 1; end

        vin_code = VIN_OK;
        k = 0;
        while (dbg_sto !== VIN_OK && k < 20 * POLL_CLKS) begin @(posedge clk); k = k + 1; end
        if (dbg_sto !== VIN_OK) $fatal(1, "[9] sto never latched VIN_OK");
        if (brownout !== 1'b0) $fatal(1, "[9] VIN_OK is below the brownout floor -- pick a higher code");
        glow_peak_duty(pk_mid);

        if (pk_hi == 0 || pk_mid == 0)
            $fatal(1, "[9] no glow at all (peaks %0d / %0d) -- the scenario proves nothing",
                   pk_hi, pk_mid);
        if (pk_hi >= pk_mid)
            $fatal(1, "[9] peak duty %0d at the HIGH rail is not below %0d at the normal rail -- vclamp is not reaching gamma_pwm",
                   pk_hi, pk_mid);
        $display("[9] ballast guard OK: peak duty %0d/256 at sto=%0d (clamped) vs %0d/256 at sto=%0d (normal)",
                 pk_hi, VIN_HIGH, pk_mid, VIN_OK);

        /* [6] whole-run gate duty: the divider only exists while converting */
        if (samples < 4)
            $fatal(1, "only %0d sense samples in the whole run, expected >= 4",
                   samples);
        if (sns_on * 50 >= sns_total)
            $fatal(1, "sns_en duty %0d/%0d clk (>= 2%%) -- the U10 gate rule",
                   sns_on, sns_total);
        $display("[6] sns_en duty OK: %0d/%0d clk over %0d samples",
                 sns_on, sns_total, samples);

        /* [7] TT wrapper smoke: same init reached its slave through the pads */
        if (tt_slave.wr_count < 5)
            $fatal(1, "tt slave saw %0d init writes, need >= 5", tt_slave.wr_count);
        if (fw_reg_tt !== 8'h1F || fw_val_tt !== 8'h52)
            $fatal(1, "tt first write {%h<=%h}, expected SOFT_RESET {1f<=52}",
                   fw_reg_tt, fw_val_tt);
        if (tt_uo_out[7] !== 1'b1)
            $fatal(1, "tt SCL not idle high after its init");
        $display("[7] TT wrapper OK: %0d writes through the pad model",
                 tt_slave.wr_count);

        $display("TB PASS: tb_top");
        $finish;
    end

endmodule
