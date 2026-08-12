// ---------------------------------------------------------------------------
// tb_i2c_master.v -- self-checking TB for i2c_master + i2c_slave_model.
//
// Checks REAL properties, $fatal on any failure, "TB PASS: tb_i2c_master"
// only if every one holds:
//   [1] write {0x2A -> reg 0x1F} lands in the slave's register file, with
//       the slave's last-written {reg,val} record and write count checked;
//   [2] read-back of reg 0x1F returns 0x2A on rdata, error-free, and the
//       pointer byte of the read did NOT count as a register write;
//   [3] a transaction to a WRONG address (nobody ACKs) finishes with done
//       AND ack_err set -- never done-without-error -- and writes nothing;
//   [4] busy asserts after start, deasserts by the time done strobes, and
//       done is exactly one clk wide; a good transaction after the failed
//       one succeeds with ack_err cleared (recovery);
//   [5] EVERY consecutive SCL rising-edge interval inside a transaction is
//       exactly 4*DIV clk (the SPEC's SCL ~= clk/(4*DIV)), and the number
//       of SCL cycles per transaction is exactly right (29 rises for a
//       write, 39 for a read, 11 for an address-NACK abort);
//   [6] the bus idles released after it all (SCL high, SDA pulled high).
//
// The board's 4.7k pull-ups (firmware/twi.h) are modelled with pullup(sda).
// Clock is 1 MHz -- the card's F_CPU and the DRH-1's nominal on-die RC.
// ---------------------------------------------------------------------------

`timescale 1ns/1ps

module tb_i2c_master;

    localparam DIV    = 5;
    localparam CLK_NS = 1000;                    // 1 MHz clk
    localparam SCL_NS = 4 * DIV * CLK_NS;        // expected SCL period (ns)

    localparam [6:0] GOOD_ADDR  = 7'h1D;         // ADXL367_ADDR on the card
    localparam [6:0] WRONG_ADDR = 7'h2C;         // nobody home

    reg        clk, rst_n;
    reg        start, rw;
    reg  [6:0] dev_addr;
    reg  [7:0] reg_addr, wdata;
    wire [7:0] rdata;
    wire       busy, done, ack_err, scl;
    wire       sda;

    pullup pu_sda (sda);                         // the board's 4.7k pull-ups

    i2c_master #(.DIV(DIV)) dut (
        .clk(clk), .rst_n(rst_n),
        .start(start), .dev_addr(dev_addr), .rw(rw),
        .reg_addr(reg_addr), .wdata(wdata),
        .rdata(rdata), .busy(busy), .done(done), .ack_err(ack_err),
        .sda(sda), .scl(scl)
    );

    i2c_slave_model #(.DEV_ADDR(GOOD_ADDR)) slave (
        .scl(scl), .sda(sda)
    );

    initial clk = 1'b0;
    always #(CLK_NS/2) clk = ~clk;

    // ---- SCL period monitor: every rise-to-rise gap inside a transaction
    //      must be exactly 4*DIV clk. Counters reset per transaction. ----
    time    t_rise;
    integer rise_seen;                           // SCL rises this transaction
    integer scl_intervals;                       // intervals verified

    initial begin
        t_rise        = 0;
        rise_seen     = 0;
        scl_intervals = 0;
    end

    always @(posedge scl) if (busy === 1'b1) begin
        if (rise_seen > 0) begin
            if (($time - t_rise) != SCL_NS)
                $fatal(1, "SCL period %0d ns, expected %0d ns (DIV=%0d)",
                       $time - t_rise, SCL_NS, DIV);
            scl_intervals = scl_intervals + 1;
        end
        rise_seen = rise_seen + 1;
        t_rise    = $time;
    end

    // ---- one full transaction, with handshake + timing bookkeeping ----
    integer guard;

    task run_txn(
        input [6:0]   a,
        input         r,
        input [7:0]   rg,
        input [7:0]   wd,
        input         exp_err,
        input integer exp_intervals
    );
        begin
            rise_seen     = 0;
            scl_intervals = 0;

            @(negedge clk);
            dev_addr = a; rw = r; reg_addr = rg; wdata = wd;
            start    = 1'b1;
            @(negedge clk);
            start    = 1'b0;
            if (busy !== 1'b1)
                $fatal(1, "busy did not assert after start");

            guard = 0;
            while (done !== 1'b1) begin
                @(negedge clk);
                guard = guard + 1;
                if (guard > 50 * 4 * DIV * 45)   // >> any legal transaction
                    $fatal(1, "timeout waiting for done");
                if (done !== 1'b1 && busy !== 1'b1)
                    $fatal(1, "busy dropped without done strobing");
            end

            // done seen: busy must already be back down, ack_err as expected
            if (busy !== 1'b0)
                $fatal(1, "busy still high while done strobes");
            if (ack_err !== exp_err)
                $fatal(1, "ack_err=%b at done, expected %b", ack_err, exp_err);

            @(negedge clk);
            if (done !== 1'b0)
                $fatal(1, "done wider than 1 clk");

            if (scl_intervals !== exp_intervals)
                $fatal(1, "SCL intervals %0d, expected %0d",
                       scl_intervals, exp_intervals);
        end
    endtask

    // ---- global watchdog ----
    initial begin
        #50000000;                               // 50 ms
        $fatal(1, "global TB watchdog expired");
    end

    // ---- stimulus + checks ----
    initial begin
        start = 1'b0; rw = 1'b0;
        dev_addr = 7'd0; reg_addr = 8'd0; wdata = 8'd0;
        rst_n = 1'b0;
        repeat (5) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);

        // [1] write 0x2A to reg 0x1F: START,addr+W,reg,data,STOP
        //     = 29 SCL rises -> 28 intervals
        run_txn(GOOD_ADDR, 1'b0, 8'h1F, 8'h2A, 1'b0, 28);
        if (slave.last_wr_reg !== 8'h1F)
            $fatal(1, "slave last_wr_reg=%h, expected 1f", slave.last_wr_reg);
        if (slave.last_wr_val !== 8'h2A)
            $fatal(1, "slave last_wr_val=%h, expected 2a", slave.last_wr_val);
        if (slave.wr_count !== 1)
            $fatal(1, "slave wr_count=%0d, expected 1", slave.wr_count);
        if (slave.regs[8'h1F] !== 8'h2A)
            $fatal(1, "slave regs[1f]=%h, expected 2a", slave.regs[8'h1F]);

        // [2] read reg 0x1F back: START,addr+W,reg,reSTART,addr+R,byte,
        //     NACK,STOP = 39 SCL rises -> 38 intervals
        run_txn(GOOD_ADDR, 1'b1, 8'h1F, 8'h00, 1'b0, 38);
        if (rdata !== 8'h2A)
            $fatal(1, "read-back rdata=%h, expected 2a", rdata);
        if (slave.wr_count !== 1)
            $fatal(1, "read txn changed wr_count (%0d) -- pointer byte must not count",
                   slave.wr_count);
        if (slave.last_wr_reg !== 8'h1F || slave.last_wr_val !== 8'h2A)
            $fatal(1, "read txn disturbed the slave write record");

        // [3] wrong address: nobody ACKs -> abort after the address byte:
        //     START,addr+W,(NACK),STOP = 11 rises -> 10 intervals,
        //     done WITH ack_err, and nothing written
        run_txn(WRONG_ADDR, 1'b0, 8'h10, 8'h55, 1'b1, 10);
        if (slave.wr_count !== 1)
            $fatal(1, "wrong-address txn reached the slave reg file");

        // [4] recovery: next good transaction succeeds, ack_err cleared
        run_txn(GOOD_ADDR, 1'b0, 8'h20, 8'h77, 1'b0, 28);
        if (slave.last_wr_reg !== 8'h20 || slave.last_wr_val !== 8'h77)
            $fatal(1, "recovery write did not land ({%h,%h})",
                   slave.last_wr_reg, slave.last_wr_val);
        if (slave.wr_count !== 2)
            $fatal(1, "slave wr_count=%0d after recovery, expected 2",
                   slave.wr_count);

        // [6] bus idles released: SCL high, SDA pulled high, master not busy
        repeat (4 * DIV * 4) @(negedge clk);
        if (scl !== 1'b1 || sda !== 1'b1)
            $fatal(1, "bus not idle after transactions (scl=%b sda=%b)",
                   scl, sda);
        if (busy !== 1'b0 || done !== 1'b0)
            $fatal(1, "master not quiescent after transactions");

        $display("TB PASS: tb_i2c_master");
        $finish;
    end

endmodule
