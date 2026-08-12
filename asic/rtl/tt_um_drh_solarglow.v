/*
 * tt_um_drh_solarglow.v -- DRH-1 companion ASIC: Tiny Tapeout wrapper
 *                          (SPEC.md pin map -- their fixed interface).
 *
 * Pure pad glue around drh1_top (which mirrors firmware/main.c and friends --
 * see rtl/drh1_top.v); no behaviour of its own. Pin map per SPEC.md:
 *
 *   ui_in : 0 = int1   1 = int2   2 = fd_n   3 = cmp_in   (7:4 unused)
 *   uo_out: 3:0 = led  4 = nfc_en 5 = sns_en 6 = chg_dis  7 = scl
 *   uio 0 : SDA, open-drain (uio_out[0] tied 0; oe = the master's sda_oe)
 *   uio 7:1: dac_code[7:1] out -- dac_code[0] is unobservable on TT
 *            (acceptable for the demo board per SPEC; the wafer.space
 *            padframe has pads to spare), so it is consumed in the unused
 *            reduction below.
 *
 * SDA plumbing: drh1_top's sda is a true inout that only ever drives low or
 * releases (i2c_master's open-drain rule). The wrapper keeps one shared net:
 * uio_in[0] -- by definition the resolved pad level, which on real silicon
 * already includes our own drive -- is buffered onto it (the pad's input
 * buffer, modelled as a plain assign), so the master samples slave ACKs and
 * pulled-up idle-highs "via the pin" exactly as in SPEC. The pad's
 * output-enable is the master's own sda_oe, delivered as a REAL PORT
 * (i2c_master.sda_oe_o -> drh1_top.sda_oe -> here) per SPEC's "oe from the
 * master's sda_oe". No hierarchical references: a hier ref is fine in
 * simulation but yosys implicitly declares it as an undriven wire, so a
 * hardening run with this wrapper as top would never drive the SDA pad.
 * Deliberately NOT done here: deriving oe from the resolved net level. That
 * looks equivalent but latches the bus low on real hardware (the chip sees
 * the low it is itself driving and never lets go).
 *
 * uio_oe is CONSTANT except the SDA bit: bits 7:1 are permanently outputs
 * (dac_code), bit 0 toggles with the master.
 *
 * The core runs at the default CLK_HZ (1 MHz nominal -- TT supplies a
 * comparable external clock); ena is the TT "design selected" strobe and,
 * like all unused inputs here, is consumed by a benign reduction so lint
 * stays quiet without leaving a floating input.
 */
module tt_um_drh_solarglow (
    input  wire [7:0] ui_in, output wire [7:0] uo_out,
    input  wire [7:0] uio_in, output wire [7:0] uio_out, output wire [7:0] uio_oe,
    input  wire ena, input wire clk, input wire rst_n
);

    wire [3:0] led;
    wire       nfc_en, sns_en, chg_dis, scl;
    wire [7:0] dac_code;
    wire [7:0] dbg_sto;      // no spare TT pins: consumed below
    wire [1:0] dbg_mode;     // no spare TT pins: consumed below

    /* ---- SDA: one shared net; uio_in[0] is the pad level (see header) ---- */
    wire sda;
    wire sda_oe;              // the master's pad oe, via drh1_top's real port
    assign sda = uio_in[0];   // pad input buffer onto the core's pin

    drh1_top core (
        .clk(clk), .rst_n(rst_n),
        .led(led),
        .sda(sda), .scl(scl),
        .int1(ui_in[0]), .int2(ui_in[1]), .fd_n(ui_in[2]),
        .nfc_en(nfc_en), .sns_en(sns_en), .chg_dis(chg_dis),
        .cmp_in(ui_in[3]), .dac_code(dac_code),
        .dbg_sto(dbg_sto), .dbg_mode(dbg_mode),
        .sda_oe(sda_oe)
    );

    /* ---- outputs, per the SPEC pin map ----------------------------------- */
    assign uo_out = {scl, chg_dis, sns_en, nfc_en, led};

    assign uio_out = {dac_code[7:1], 1'b0};      // SDA pad only ever drives low
    assign uio_oe  = {7'b1111111,                // dac_code[7:1]: always driven
                      sda_oe};                   // SDA: the master's own oe

    /* ---- unused inputs: benign reduction (no floating inputs, no lint) --- */
    wire unused = &{ena, ui_in[7:4], uio_in[7:1],
                    dbg_sto, dbg_mode, dac_code[0], 1'b1};

endmodule
