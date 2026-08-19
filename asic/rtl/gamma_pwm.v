/*
 * gamma_pwm.v -- DRH-1 companion ASIC: four-channel gamma-corrected LED PWM.
 *
 * MIRRORS firmware/led.c (the card's working behaviour is the spec):
 *   - gamma(): led.c's gamma2() exactly -- (x*x)>>8, the cheap gamma-2
 *     approximation of x^2/255 named in SPEC.md (off by at most 1 LSB from
 *     the literal /255; monotonic, 0 -> 0, 255 -> 254).
 *   - mode 01 "breathe": led_breathe()'s smooth in/out envelope, all four
 *     channels in phase (the tap-to-wake glow).
 *   - mode 10 "sweep": led_sweep()'s left->right chase, rendered here as the
 *     same triangle envelope with a 64-step (90 degree) phase lag per channel
 *     so neighbours cross as one dims and the next brightens. (On the card,
 *     physical left->right D2..D5 is channel order 3,2,1,0 -- see led.c's
 *     phys_ch[]; the analog pad ring owns that mapping, the RTL offsets by
 *     channel index.)
 *   - mode 11 "dim solid": constant small duty (SW2-visible "alive" tell).
 *   - PWM: free-running 8-bit counter on clk -> ~3.9 kHz at 1 MHz, the same
 *     255-count period as TCA0 split mode (LPER=HPER=255, DIV1) in led.c.
 *
 * Envelope geometry: SPEC's "triangle 0..255..0 stepped on tick_env" with
 * per-channel offsets of 64 steps and "90 degree" sweep spacing pins the
 * envelope period at 256 tick_env steps (2 s at 128 Hz). The triangle
 * therefore steps its amplitude by 2 per tick (0..254..0 -- peak 254, one
 * LSB shy of 255, the price of the 2/step slope), so a 64-step offset is a
 * true quarter period and led[0]/led[2] (128 steps apart) breathe in
 * antiphase. The master phase free-runs in every mode; mode changes take
 * effect within 2 clks.
 *
 * Polarity: led[] is ACTIVE-HIGH into the four 16 mA sink cells -- duty 0 =
 * line low = LED dark. The AVR's INVEN pad-invert trick (load-bearing on the
 * card, see led.h) is an AVR pad artifact and deliberately does NOT carry
 * over; the dark-at-reset guarantee here is duty regs reset to 0.
 *
 * Mode-off is SAME-CYCLE: the led outputs are forced low combinationally
 * whenever mode == 00 (a final AND on the output path), on top of the duty
 * regs clearing one clk later. Load-bearing for dormancy: when vcrit cuts a
 * live glow, wake_fsm registers brownout and led_mode=00 on the same edge,
 * and without the AND the still-loaded duty regs would drive the LEDs for
 * one clk while brownout is already high. tb_top's dormancy-dark invariant
 * pins this.
 *
 * Verilog-2001, single clock, synchronous reset, no latches, no initial.
 */
module gamma_pwm #(
    parameter [7:0] CLAMP_PEAK = 8'd225   // board.h GLOW_CLAMP_PEAK -- see header
)(
    input  wire clk, input wire rst_n,
    input  wire tick_env,
    input  wire [1:0] mode,   // 00 off | 01 breathe (all 4 in phase) | 10 sweep (90 deg offsets) | 11 dim solid
    input  wire clamp_en,     // sense_seq.vclamp: rail above the ballast-guard threshold
    output wire [3:0] led     // active-high to the four 16 mA sink cells
);

    localparam [1:0] MODE_OFF     = 2'b00,
                     MODE_BREATHE = 2'b01,
                     MODE_SWEEP   = 2'b10,
                     MODE_DIM     = 2'b11;

    localparam [7:0] DIM_DUTY = 8'd16;   // mode 11: 16/256 ~ 6% -- "dim solid"
    localparam [7:0] CH_OFFS  = 8'd64;   // sweep: 64 envelope steps = 90 deg

    /* triangle envelope: 8-bit phase -> amplitude 0..254..0 over a 256-step
     * period (up 0..127, down 128..255; slope 2 per step). */
    function [7:0] tri255 (input [7:0] p);
        begin
            if (p[7]) tri255 = (8'd255 - p) << 1;
            else      tri255 = p << 1;
        end
    endfunction

    /* perceptual ramp -- led.c gamma2(): out = (in*in) >> 8, the cheap x^2/255. */
    function [7:0] gamma (input [7:0] x);
        reg [15:0] sq;
        begin
            sq    = x * x;        // 16-bit context: no truncation
            gamma = sq[15:8];
        end
    endfunction

    /* THE BALLAST GUARD, actuation half -- led.c has no equivalent because the
     * card applies it one level up, in sense.c's sense_glow_peak(). This is the
     * same idea in the same shape: ONE function that every animation's amplitude
     * passes through on its way to a duty register, so no mode can route around
     * it and a mode added later inherits it by construction. A ceiling, not a
     * rescale -- exactly the firmware's `if (peak > GLOW_CLAMP_PEAK) peak =
     * GLOW_CLAMP_PEAK`, which flat-tops the envelope rather than shrinking it.
     * That is the right shape for the published bound, because the bound is
     * computed at a HELD peak: 70 mW x 225/255 = 61.8 mW < 62.5 mW rating. A
     * flat top at CLAMP_PEAK forever IS that worst case, so clamping the
     * instantaneous duty buys the identical guarantee as clamping the peak. */
    function [7:0] ballast (input [7:0] d);
        begin
            ballast = (clamp_en && d > CLAMP_PEAK) ? CLAMP_PEAK : d;
        end
    endfunction

    reg [7:0] phase;     // master envelope phase, steps on tick_env
    reg [7:0] pwm_cnt;   // free-running 8-bit PWM counter on clk
    reg [7:0] duty0, duty1, duty2, duty3;

    always @(posedge clk) begin
        if (!rst_n) begin
            phase <= 8'd0;
            duty0 <= 8'd0;
            duty1 <= 8'd0;
            duty2 <= 8'd0;
            duty3 <= 8'd0;
        end else begin
            if (tick_env)
                phase <= phase + 8'd1;
            case (mode)
                MODE_OFF: begin
                    duty0 <= 8'd0;
                    duty1 <= 8'd0;
                    duty2 <= 8'd0;
                    duty3 <= 8'd0;
                end
                MODE_BREATHE: begin        // all four in phase (led_breathe)
                    duty0 <= ballast(gamma(tri255(phase)));
                    duty1 <= ballast(gamma(tri255(phase)));
                    duty2 <= ballast(gamma(tri255(phase)));
                    duty3 <= ballast(gamma(tri255(phase)));
                end
                MODE_SWEEP: begin          // 90-degree offsets (led_sweep chase)
                    duty0 <= ballast(gamma(tri255(phase)));
                    duty1 <= ballast(gamma(tri255(phase + CH_OFFS)));
                    duty2 <= ballast(gamma(tri255(phase + (CH_OFFS << 1))));
                    duty3 <= ballast(gamma(tri255(phase + (CH_OFFS << 1) + CH_OFFS)));
                end
                MODE_DIM: begin            // constant small duty
                    duty0 <= ballast(DIM_DUTY);
                    duty1 <= ballast(DIM_DUTY);
                    duty2 <= ballast(DIM_DUTY);
                    duty3 <= ballast(DIM_DUTY);
                end
            endcase
        end
    end

    always @(posedge clk) begin
        if (!rst_n) pwm_cnt <= 8'd0;
        else        pwm_cnt <= pwm_cnt + 8'd1;
    end

    /* duty N -> exactly N high clks per 256-clk PWM period; duty 0 -> solid low.
     * The mode_on AND makes mode 00 dark on the SAME cycle the mode changes
     * (the duty regs only clear one clk later -- see header, dormancy rule). */
    wire mode_on = (mode != MODE_OFF);
    assign led[0] = mode_on & (pwm_cnt < duty0);
    assign led[1] = mode_on & (pwm_cnt < duty1);
    assign led[2] = mode_on & (pwm_cnt < duty2);
    assign led[3] = mode_on & (pwm_cnt < duty3);

endmodule
