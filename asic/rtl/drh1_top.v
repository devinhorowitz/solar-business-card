/*
 * drh1_top.v -- DRH-1 companion ASIC: digital core top level
 *               (SPEC.md port contract -- do not deviate).
 *
 * MIRRORS firmware/main.c's bring-up order and standing structure (the card's
 * working firmware is the spec -- main.c header, "Bring-up order below follows
 * hardware doc section 7 exactly"):
 *
 *   main.c                            here
 *   -------------------------------   -------------------------------------
 *   led_init() -- TCA dark at reset   gamma_pwm: duty regs reset to 0
 *   adxl367_init_tap() over TWI0      init_seq -> i2c_master (owns the bus:
 *                                       this experiment has no second master;
 *                                       arbitration is v-next, per SPEC)
 *   RTC PIT 1 s poll + TCB env tick   clkdiv: tick_poll / tick_env
 *   sense.c deferred-read + U10 gate  sense_seq -> sar_ctrl (+ off-chip
 *                                       comparator/DAC stubs via cmp_in /
 *                                       dac_code -- analog is NOT claimed)
 *   the tap/dormancy/NFC event loop   wake_fsm
 *
 * Wiring notes (everything here is glue; behaviour lives in the leaves):
 *   - init_seq is kicked exactly ONCE, on the first clk after rst_n release
 *     (main.c calls adxl367_init_tap() once out of reset). done_all is a
 *     sticky level -> wake_fsm.init_done, which is what lets wake_fsm leave
 *     WAIT_INIT and stay out.
 *   - If init parks failed (accel not talking: init_seq's fail after its
 *     retry), init_done never rises and wake_fsm never arms -- the chip stays
 *     dark and quiet. Same net effect as the card with a dead ADXL367: no
 *     tap source, no glow. fail/active are observable only hierarchically
 *     in this revision (no spare debug pins on the TT wrapper).
 *   - wake_fsm.force_sense -> sense_seq.force_rd is main.c's "gate first,
 *     convert only if a glow can still fire" event path; sense_seq.vlow /
 *     .vcrit close the loop back into wake_fsm (rail-gated glow, dormancy).
 *   - sense_seq.vclamp -> gamma_pwm.clamp_en is the BALLAST GUARD, and it is
 *     the one sense flag that does NOT go to wake_fsm: it changes how bright
 *     an animation is, not whether one runs, so it lands on the duty path
 *     instead of the state machine. Firmware analogue: sense_glow_peak()'s
 *     high-side clamp (board.h USE_BALLAST_GUARD / GLOW_CLAMP_STO_MV / PEAK).
 *   - dbg_sto / dbg_mode are debug taps of sense_seq.sto_q and the live LED
 *     mode -- pure fan-out, no logic.
 *
 * CLK_HZ is a pass-through to clkdiv (default 1 MHz, the nominal on-die RC).
 * The PORT list is SPEC.md's plus one appended output, sda_oe -- the I2C
 * master's pad output-enable plumbed out as a real port so wrappers (the TT
 * one first) never need a hierarchical reference, which yosys would silently
 * turn into an undriven implicit wire if the wrapper were synthesis top.
 * The parameter exists so tb_top.v can run the whole core at a reduced tick
 * scale (a 1 Hz tick_poll at 1 MHz is ~1e6 clk per poll -- unsimulatable at
 * scenario length).
 *
 * Verilog-2001, single clock, synchronous rst_n, no latches, no initial in
 * RTL, strobes exactly one clk wide (SPEC.md global rules).
 */
module drh1_top #(parameter CLK_HZ = 1000000) (
    input  wire clk, input wire rst_n,
    output wire [3:0] led,
    inout  wire sda, output wire scl,
    input  wire int1, input wire int2, input wire fd_n,
    output wire nfc_en, output wire sns_en, output wire brownout,
    input  wire cmp_in, output wire [7:0] dac_code,
    output wire [7:0] dbg_sto, output wire [1:0] dbg_mode,
    output wire sda_oe               // i2c_master's pad output-enable, exported
);                                   //   for wrappers/padframes (no hier refs)

    /* ---- ticks ---------------------------------------------------------- */
    wire tick_env, tick_poll;

    clkdiv #(.CLK_HZ(CLK_HZ)) u_clkdiv (
        .clk(clk), .rst_n(rst_n),
        .tick_env(tick_env), .tick_poll(tick_poll)
    );

    /* ---- one-shot init kick (main.c runs adxl367_init_tap() once) ------- */
    // booted is 0 only until the first posedge after reset release, so
    // iseq_start is a true 1-clk strobe into init_seq's S_IDLE.
    reg booted;
    always @(posedge clk) begin
        if (!rst_n) booted <= 1'b0;
        else        booted <= 1'b1;
    end
    wire iseq_start = ~booted;

    /* ---- accel config: init_seq owns the I2C master --------------------- */
    wire        init_active;     // observable hierarchically only (see header)
    wire        init_done_all;
    wire        init_fail;       // parked-failed: wake_fsm never arms
    wire        m_start, m_rw;
    wire [6:0]  m_dev;
    wire [7:0]  m_reg, m_wdata;
    wire        m_busy, m_done, m_ack_err;
    wire [7:0]  m_rdata;         // write-only sequencer: read data unused

    init_seq u_init (
        .clk(clk), .rst_n(rst_n), .start(iseq_start),
        .active(init_active), .done_all(init_done_all), .fail(init_fail),
        .m_start(m_start), .m_dev(m_dev), .m_rw(m_rw),
        .m_reg(m_reg), .m_wdata(m_wdata),
        .m_busy(m_busy), .m_done(m_done), .m_ack_err(m_ack_err)
    );

    i2c_master #(.DIV(5)) u_i2c (      // ~50 kHz SCL at the nominal 1 MHz clk
        .clk(clk), .rst_n(rst_n),
        .start(m_start), .dev_addr(m_dev), .rw(m_rw),
        .reg_addr(m_reg), .wdata(m_wdata),
        .rdata(m_rdata), .busy(m_busy), .done(m_done), .ack_err(m_ack_err),
        .sda(sda), .sda_oe_o(sda_oe), .scl(scl)
    );

    /* ---- STO sense chain: sequencer + SAR (analog stubs off-chip) ------- */
    wire       sar_go, sar_done;
    wire [7:0] sar_result;
    wire       vlow, vcrit, vclamp;
    wire       force_sense;

    sar_ctrl u_sar (
        .clk(clk), .rst_n(rst_n), .go(sar_go),
        .cmp_in(cmp_in),
        .dac_code(dac_code),
        .result(sar_result), .done(sar_done), .busy()   // busy: sense_seq
    );                                                  //   sequences on done

    sense_seq u_sense (                // SETTLE/POLLS/thresholds: SPEC defaults
        .clk(clk), .rst_n(rst_n),
        .tick_poll(tick_poll), .tick_env(tick_env),
        .force_rd(force_sense),
        .sar_result(sar_result), .sar_done(sar_done),
        .sar_go(sar_go), .sns_en(sns_en),
        .sto_q(dbg_sto), .vlow(vlow), .vcrit(vcrit), .vclamp(vclamp)
    );

    /* ---- supervisor: main.c's dormancy / tap / NFC loop ----------------- */
    wake_fsm u_wake (                  // GLOW/NFC hold polls: SPEC defaults
        .clk(clk), .rst_n(rst_n),
        .tick_poll(tick_poll),
        .int1(int1), .int2(int2), .fd_n(fd_n),
        .vlow(vlow), .vcrit(vcrit), .init_done(init_done_all),
        .led_mode(dbg_mode), .force_sense(force_sense),
        .nfc_en(nfc_en), .brownout(brownout)
    );

    /* ---- LEDs ------------------------------------------------------------ */
    gamma_pwm u_pwm (
        .clk(clk), .rst_n(rst_n),
        .tick_env(tick_env),
        .mode(dbg_mode),               // the live wake_fsm mode, also the debug tap
        .clamp_en(vclamp),             // ballast guard: sense measures, gamma_pwm acts
        .led(led)
    );

endmodule
