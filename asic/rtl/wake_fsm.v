/*
 * wake_fsm.v -- DRH-1 companion ASIC: dormancy / tap / NFC supervisor.
 *
 * MIRRORS firmware/main.c (the card's dormancy/tap event loop), quantized
 * onto tick_poll the way main.c hangs off the RTC PIT:
 *   - WAIT_INIT -> IDLE: main.c does not arm its event ISRs until
 *     adxl367_init_tap() has run; here nothing responds until init_done
 *     (a LEVEL -- drh1_top wires init_seq's sticky done_all in).
 *   - tap (rising int1, main.c's f_tap on PF0): force_sense strobes -- the
 *     silicon version of main.c's "gate first, convert only if a glow can
 *     still fire" fresh rail read via sense_seq's force_rd event path --
 *     then, if the rail is above the glow floor (!vlow), breathe (mode 01)
 *     for GLOW_POLLS polls: main.c's rail-gated led_breathe on tap.
 *     DESIGN NOTE, stated because the contract has no sense-done handshake:
 *     the glow decision samples the STANDING vlow latch in the tap cycle
 *     (sense_seq's last sample); the force_rd refresh lands a few env ticks
 *     later and gates the NEXT event. The card blocks on its ADC read; a
 *     latch-free single-clock FSM cannot, so the standing level decides.
 *   - second tap during the glow -> sweep (mode 10): the card resolves
 *     single-vs-double IN the accel's hardware (adxl367.c header) and plays
 *     the DTAP signature; this FSM resolves the second tap itself, so the
 *     ROM in init_seq.v does not program the hw double-tap engine. The sweep
 *     runs GLOW_POLLS polls (contract gives it no length of its own; the
 *     glow window is the one poll-denominated animation length here);
 *     further taps during the sweep are ignored.
 *   - vcrit -> DORMANT: mode 00, `brownout` asserted, taps ignored, exit
 *     only when vcrit drops. This is the silicon cousin of main.c's
 *     brownout floor (every glow gated by VS_GLOW_FLOOR_MV) -- `brownout`
 *     is the TELL that the tank sits at that floor and the LED loads must
 *     stay off. Recovery returns to IDLE with it released.
 *     vcrit is honoured from IDLE/GLOW/SWEEP (it cuts an animation dead);
 *     during WAIT_INIT it is ignored -- init is still sequencing and there
 *     is no armed behaviour to suppress.
 *     THE NAME IS LOAD-BEARING, and this output is a STATUS TELL, not a
 *     charge control. It was called chg_dis until 2026-08-19, which is
 *     the same name as the card's own CHG_DIS_G net (PA4 -> Q2 gate) --
 *     and that one is the opposite kind of thing: a charge-INHIBIT
 *     CONTROL, driven from the FD both-edge handler to quiet the >=10 MHz
 *     DC-DC for an NFC read, nothing to do with brownout. Wire this pin
 *     to that net and a brownout disables harvest exactly when the tank
 *     is empty: the cold-start deadlock that the 2026-07-23 fix and R18's
 *     gate pulldown exist to prevent, re-created in silicon. The miswire
 *     was dangerous BECAUSE the two names matched, so no reviewer and no
 *     bench could see it. This output must never reach EN_STO_CH.
 *   - fd_n low (NFC field present, main.c's PA6/FD, active-low, field-
 *     powered) -> nfc_en asserted and held for NFC_HOLD_POLLS polls AFTER
 *     the field is last seen, then off: main.c's transient NFC-rail window
 *     (the tag reads unpowered; the rail only feeds the FD/I2C extras --
 *     same as the card, per SPEC). The hold counter reloads for as long as
 *     fd_n stays low, so a held field never drops the rail mid-exchange.
 *     Independent of the main state by design: SPEC scopes DORMANT to
 *     "taps ignored", and the card's FD path likewise works through
 *     everything short of face-down deep sleep.
 *   - int2 (activity -> motion soft-breath in main.c) is accepted for the
 *     port contract but RESERVED (unused) in this revision: SPEC.md's
 *     wake_fsm behaviour clause defines no int2 response, and init_seq's
 *     8-entry ROM leaves the activity engine unconfigured to match.
 *
 * Poll-count semantics (pinned here, asserted by tb_wake_fsm.v): a window
 * of K polls loads its counter with K at the triggering event and counts
 * one per tick_poll; the output condition ends on the K-th tick_poll after
 * the trigger. Parameters must fit the 8-bit counters (1..255).
 *
 * Verilog-2001, single clock, synchronous rst_n, no latches, no initial in
 * RTL, strobes (force_sense) exactly one clk wide (SPEC.md global rules).
 */
module wake_fsm #(
    parameter GLOW_POLLS = 4, parameter NFC_HOLD_POLLS = 8
)(
    input  wire clk, input wire rst_n,
    input  wire tick_poll,
    input  wire int1, input wire int2, input wire fd_n,
    input  wire vlow, input wire vcrit, input wire init_done,
    output reg  [1:0] led_mode, output reg force_sense,
    output reg  nfc_en, output reg brownout
);

    localparam [1:0] MODE_OFF     = 2'b00,
                     MODE_BREATHE = 2'b01,
                     MODE_SWEEP   = 2'b10;

    localparam [2:0] ST_WAIT_INIT = 3'd0,
                     ST_IDLE      = 3'd1,
                     ST_GLOW      = 3'd2,
                     ST_SWEEP     = 3'd3,
                     ST_DORMANT   = 3'd4;

    // 8-bit copies of the poll parameters (sized once, counters match)
    localparam [7:0] GLOW_P = GLOW_POLLS;
    localparam [7:0] NFC_P  = NFC_HOLD_POLLS;

    reg [2:0] state;
    reg [7:0] anim_cnt;   // polls left in the GLOW / SWEEP window
    reg [7:0] nfc_cnt;    // polls left on the NFC rail hold
    reg       int1_q;     // tap edge detector history

    wire tap = int1 & ~int1_q;   // rising int1 (PF0-rising in main.c terms)

    always @(posedge clk) begin
        if (!rst_n) begin
            state       <= ST_WAIT_INIT;
            anim_cnt    <= 8'd0;
            nfc_cnt     <= 8'd0;
            int1_q      <= 1'b0;
            led_mode    <= MODE_OFF;   // dark at reset -- same guarantee gamma_pwm
            force_sense <= 1'b0;       //   makes with its duty regs
            nfc_en      <= 1'b0;
            brownout    <= 1'b0;
        end else begin
            int1_q      <= int1;       // runs in every state: a pre-init or
                                       // in-dormancy tap is consumed, never
                                       // latched for replay
            force_sense <= 1'b0;       // default: 1-clk strobe

            /* ---- NFC rail hold: independent of the main state ---- */
            if (!fd_n) begin
                nfc_en  <= 1'b1;       // field present: rail up, counter topped
                nfc_cnt <= NFC_P;
            end else if (nfc_en && tick_poll) begin
                if (nfc_cnt <= 8'd1) begin
                    nfc_en  <= 1'b0;   // NFC_HOLD_POLLS-th poll after release
                    nfc_cnt <= 8'd0;
                end else begin
                    nfc_cnt <= nfc_cnt - 8'd1;
                end
            end

            /* ---- main supervisor ---- */
            case (state)

                ST_WAIT_INIT: begin            // nothing armed until the accel
                    led_mode <= MODE_OFF;      //   config sequence is done
                    brownout <= 1'b0;
                    if (init_done)
                        state <= ST_IDLE;
                end

                ST_IDLE: begin
                    led_mode <= MODE_OFF;
                    if (vcrit) begin
                        state    <= ST_DORMANT;
                        brownout <= 1'b1;
                    end else if (tap) begin
                        force_sense <= 1'b1;           // fresh rail read (event path)
                        if (!vlow) begin               // rail-gated glow (standing latch)
                            state    <= ST_GLOW;
                            led_mode <= MODE_BREATHE;
                            anim_cnt <= GLOW_P;
                        end
                        // vlow: stay dark, stay IDLE -- main.c's peak==0 branch
                    end
                end

                ST_GLOW: begin
                    if (vcrit) begin                   // brownout cuts the animation
                        state    <= ST_DORMANT;
                        led_mode <= MODE_OFF;
                        brownout <= 1'b1;
                    end else if (tap) begin            // second tap -> sweep signature
                        state    <= ST_SWEEP;
                        led_mode <= MODE_SWEEP;
                        anim_cnt <= GLOW_P;
                    end else if (tick_poll) begin
                        if (anim_cnt <= 8'd1) begin
                            state    <= ST_IDLE;       // GLOW_POLLS-th poll ends it
                            led_mode <= MODE_OFF;
                        end else begin
                            anim_cnt <= anim_cnt - 8'd1;
                        end
                    end
                end

                ST_SWEEP: begin                        // taps ignored during sweep
                    if (vcrit) begin
                        state    <= ST_DORMANT;
                        led_mode <= MODE_OFF;
                        brownout <= 1'b1;
                    end else if (tick_poll) begin
                        if (anim_cnt <= 8'd1) begin
                            state    <= ST_IDLE;
                            led_mode <= MODE_OFF;
                        end else begin
                            anim_cnt <= anim_cnt - 8'd1;
                        end
                    end
                end

                ST_DORMANT: begin                      // mode 00, taps ignored
                    led_mode <= MODE_OFF;
                    if (!vcrit) begin
                        brownout <= 1'b0;              // recovery: tell clears,
                        state    <= ST_IDLE;           //   taps live again
                    end else begin
                        brownout <= 1'b1;
                    end
                end

                default: state <= ST_WAIT_INIT;        // unreachable encodings
            endcase
        end
    end

endmodule
