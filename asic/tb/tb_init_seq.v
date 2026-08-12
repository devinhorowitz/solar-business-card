/*
 * tb_init_seq.v -- self-checking testbench for init_seq (DRH-1).
 *
 * The i2c_master handshake (m_busy / m_done / m_ack_err) is STUBBED directly
 * per the task brief -- no i2c bus involved. The stub honours the real
 * master's timing shape: busy rises after the issue, done is a 1-cycle
 * strobe with ack_err valid alongside it.
 *
 * Checks (all $fatal on failure -- real properties, not just activity):
 *   A. Clean run: all N ROM entries issued IN ORDER, each {reg, val}
 *      matching the golden copy of the ROM held HERE (a deliberate second
 *      copy: an accidental ROM edit in the RTL goes red); every issue
 *      carries dev addr 0x1D and m_rw == write; exactly ONE m_start strobe
 *      per entry (monitor faults any m_start while the stub is busy, and
 *      any strobe wider than 1 clk); no issue before start; active high
 *      across the run and low after; done_all == 0 until the last entry
 *      completes, then 1 with fail == 0; parked after (no further m_start).
 *   B. Recoverable NACK: ack_err injected on entry 2 -> exactly one retry
 *      of the SAME entry (issue log shows entry 2 twice, then entry 3 --
 *      proving one retry, not zero, not two), sequence completes with
 *      done_all == 1, fail == 0, N+1 total issues.
 *   C. Fatal NACK: ack_err on entry 2 twice -> fail == 1, done_all == 0,
 *      active == 0, exactly 4 issues (entries 0, 1, 2, retry-2) and NOT ONE
 *      more over a long park watch.
 *
 * All TB sampling/driving is on negedge clk (NBA-updated DUT state stable),
 * matching the tb_gamma_pwm.v house style.
 */
`timescale 1ns/1ps

module tb_init_seq;

    localparam integer N = 8;   // must match init_seq.v's ROM depth

    reg         clk = 1'b0;
    reg         rst_n = 1'b0;
    reg         start = 1'b0;
    wire        active, done_all, fail;
    wire        m_start;
    wire [6:0]  m_dev;
    wire        m_rw;
    wire [7:0]  m_reg, m_wdata;
    reg         m_busy = 1'b0, m_done = 1'b0, m_ack_err = 1'b0;

    init_seq dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .active(active), .done_all(done_all), .fail(fail),
        .m_start(m_start), .m_dev(m_dev), .m_rw(m_rw),
        .m_reg(m_reg), .m_wdata(m_wdata),
        .m_busy(m_busy), .m_done(m_done), .m_ack_err(m_ack_err)
    );

    always #5 clk = ~clk;

    // watchdog
    initial begin
        #20_000_000;
        $fatal(1, "TB TIMEOUT: did not reach TB PASS");
    end

    /* ---- golden ROM copy (mirror of init_seq.v's table; PROVISIONAL values
     *      from firmware/adxl367.h, POWER_CTL in SPEC's wake-up mode) ---- */
    reg [7:0] exp_reg [0:N-1];
    reg [7:0] exp_val [0:N-1];
    initial begin
        exp_reg[0] = 8'h1F; exp_val[0] = 8'h52;   // SOFT_RESET
        exp_reg[1] = 8'h2C; exp_val[1] = 8'h23;   // FILTER_CTL
        exp_reg[2] = 8'h2F; exp_val[2] = 8'h30;   // TAP_THRESH
        exp_reg[3] = 8'h30; exp_val[3] = 8'h10;   // TAP_DUR
        exp_reg[4] = 8'h43; exp_val[4] = 8'h20;   // AXIS_MASK
        exp_reg[5] = 8'h3A; exp_val[5] = 8'h01;   // INTMAP1_UPPER
        exp_reg[6] = 8'h2B; exp_val[6] = 8'h10;   // INTMAP2_LOWER
        exp_reg[7] = 8'h2D; exp_val[7] = 8'h0A;   // POWER_CTL (wake-up mode)
    end

    /* ---- issue monitor: logs every m_start, faults protocol breaks ---- */
    integer   n_issued;      // strobes seen by the monitor (the one observer)
    integer   n_served;      // transactions the serve() stub has completed
    reg [7:0] log_reg [0:31];
    reg [7:0] log_val [0:31];
    reg       prev_start = 1'b0;
    reg       mon_on = 1'b0;

    always @(negedge clk) begin
        if (mon_on) begin
            if (m_start === 1'bx)
                $fatal(1, "m_start is X");
            if (m_start === 1'b1) begin
                if (prev_start)
                    $fatal(1, "m_start high 2 consecutive cycles (not a 1-clk strobe)");
                if (m_busy)
                    $fatal(1, "m_start asserted while master busy (double issue)");
                if (m_dev !== 7'h1D)
                    $fatal(1, "issue %0d: dev addr %h != 0x1D", n_issued, m_dev);
                if (m_rw !== 1'b0)
                    $fatal(1, "issue %0d: m_rw %b != write", n_issued, m_rw);
                if (^m_reg === 1'bx || ^m_wdata === 1'bx)
                    $fatal(1, "issue %0d: m_reg/m_wdata has X bits", n_issued);
                log_reg[n_issued] = m_reg;
                log_val[n_issued] = m_wdata;
                n_issued = n_issued + 1;
            end
            prev_start = (m_start === 1'b1);
        end
    end

    /* ---- helpers ---- */
    task do_reset;
        begin
            mon_on = 1'b0;
            @(negedge clk);
            rst_n = 1'b0;
            m_busy = 1'b0; m_done = 1'b0; m_ack_err = 1'b0; start = 1'b0;
            repeat (4) @(negedge clk);
            n_issued = 0; n_served = 0; prev_start = 1'b0;
            mon_on = 1'b1;
            rst_n = 1'b1;
            @(negedge clk);
        end
    endtask

    task pulse_start;
        begin
            @(negedge clk);
            start = 1'b1;
            @(negedge clk);
            start = 1'b0;
        end
    endtask

    // Serve one transaction. Sequenced off the monitor's issue COUNT, not the
    // m_start wire itself: the strobe is 1 clk wide and may already have come
    // and gone (the monitor logged it) before this task is entered. Hold busy
    // a few cycles, then strobe done with ack_err = do_err.
    task serve (input do_err);
        begin
            while (n_issued <= n_served) @(negedge clk);
            n_served = n_served + 1;
            @(negedge clk);                 // clear of the strobe cycle
            m_busy = 1'b1;
            repeat (5) @(negedge clk);      // transaction "in flight"
            m_ack_err = do_err;
            m_done = 1'b1;
            @(negedge clk);
            m_done = 1'b0;
            m_busy = 1'b0;
        end
    endtask

    integer i;

    initial begin
        /* ================= A: clean run ================= */
        do_reset;

        // quiet before start: no issue, flags low
        repeat (20) @(negedge clk);
        if (n_issued != 0)        $fatal(1, "A: issued %0d entries before start", n_issued);
        if (active !== 1'b0)      $fatal(1, "A: active high before start");
        if (done_all !== 1'b0)    $fatal(1, "A: done_all high before start");
        if (fail !== 1'b0)        $fatal(1, "A: fail high before start");

        pulse_start;
        @(negedge clk);
        if (active !== 1'b1)      $fatal(1, "A: active did not rise on start");

        for (i = 0; i < N; i = i + 1) begin
            if (done_all !== 1'b0)
                $fatal(1, "A: done_all high before entry %0d completed", i);
            serve(1'b0);
        end

        repeat (3) @(negedge clk);
        if (done_all !== 1'b1)    $fatal(1, "A: done_all not set after last entry");
        if (fail !== 1'b0)        $fatal(1, "A: fail set on a clean run");
        if (active !== 1'b0)      $fatal(1, "A: active still high after done_all");
        if (n_issued != N)        $fatal(1, "A: %0d issues != N = %0d", n_issued, N);
        for (i = 0; i < N; i = i + 1) begin
            if (log_reg[i] !== exp_reg[i] || log_val[i] !== exp_val[i])
                $fatal(1, "A: entry %0d = {%h,%h}, expected {%h,%h} (ROM order broken)",
                       i, log_reg[i], log_val[i], exp_reg[i], exp_val[i]);
        end

        // parked: no further issues, done_all sticky
        repeat (200) @(negedge clk);
        if (n_issued != N)        $fatal(1, "A: issued again after done_all (park broken)");
        if (done_all !== 1'b1)    $fatal(1, "A: done_all did not stay sticky");
        $display("A OK: %0d entries in ROM order to dev 0x1D (write), one m_start each; done_all sticky, fail 0, parked", N);

        /* ============ B: NACK on entry 2, retry ACKs ============ */
        do_reset;
        pulse_start;

        serve(1'b0);                        // entry 0
        serve(1'b0);                        // entry 1
        serve(1'b1);                        // entry 2 -> NACK
        serve(1'b0);                        // the one retry of entry 2 -> ACK
        repeat (2) @(negedge clk);
        if (fail !== 1'b0)        $fatal(1, "B: fail set although the retry ACKed");
        for (i = 3; i < N; i = i + 1)
            serve(1'b0);                    // entries 3..N-1

        repeat (3) @(negedge clk);
        if (done_all !== 1'b1)    $fatal(1, "B: done_all not set after recovered run");
        if (fail !== 1'b0)        $fatal(1, "B: fail set after recovered run");
        if (n_issued != N + 1)    $fatal(1, "B: %0d issues != N+1 = %0d (exactly one retry)", n_issued, N + 1);
        // issue log: 0, 1, 2, 2 (retry), 3, ... -- the retry is the SAME entry
        if (log_reg[2] !== exp_reg[2] || log_val[2] !== exp_val[2])
            $fatal(1, "B: NACKed issue was not entry 2");
        if (log_reg[3] !== exp_reg[2] || log_val[3] !== exp_val[2])
            $fatal(1, "B: retry {%h,%h} != entry 2 {%h,%h} (must reissue the same entry)",
                   log_reg[3], log_val[3], exp_reg[2], exp_val[2]);
        for (i = 3; i < N; i = i + 1)
            if (log_reg[i + 1] !== exp_reg[i] || log_val[i + 1] !== exp_val[i])
                $fatal(1, "B: post-retry entry %0d out of order", i);
        $display("B OK: NACK on entry 2 -> exactly one retry of entry 2, then 3..%0d; done_all 1, fail 0, %0d issues", N - 1, N + 1);

        /* ============ C: NACK on entry 2 twice -> fail, park ============ */
        do_reset;
        pulse_start;

        serve(1'b0);                        // entry 0
        serve(1'b0);                        // entry 1
        serve(1'b1);                        // entry 2 -> NACK
        serve(1'b1);                        // retry   -> NACK again
        repeat (3) @(negedge clk);
        if (fail !== 1'b1)        $fatal(1, "C: fail not set after two NACKs on one entry");
        if (done_all !== 1'b0)    $fatal(1, "C: done_all set on a failed run");
        if (active !== 1'b0)      $fatal(1, "C: active still high after fail-park");
        if (n_issued != 4)        $fatal(1, "C: %0d issues != 4 (0, 1, 2, retry-2)", n_issued);

        repeat (300) @(negedge clk);
        if (n_issued != 4)        $fatal(1, "C: issued again after fail (park broken)");
        if (fail !== 1'b1)        $fatal(1, "C: fail did not stay sticky");
        $display("C OK: double NACK on entry 2 -> fail 1, done_all 0, 4 issues total, parked for good");

        $display("TB PASS: tb_init_seq");
        $finish;
    end

endmodule
