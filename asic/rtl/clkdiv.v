/*
 * clkdiv.v -- DRH-1 companion ASIC: master tick generation (SPEC.md port contract).
 *
 * Mirrors the card firmware's two timebases (firmware/main.c + firmware/led.c):
 *   - tick_poll (1 Hz, 1-cycle strobe) is main.c's RTC PIT poll cadence
 *     (NORMAL_PIT_gc = CYC1024 off the 1.024 kHz ULP -> 1.0 s): the "sample
 *     light / fold counters / run the wake loop" heartbeat.
 *   - tick_env (128 Hz, 1-cycle strobe) is the envelope + settle timebase:
 *     led.c steps its breathing envelope off a 1 ms TCB tick, and sense.c's
 *     deferred-read RC settle is a wait measured in the same small-ms units;
 *     both quantize onto this one 128 Hz strobe in silicon (SPEC sense_seq
 *     counts 5 of these for its ~39 ms settle).
 *
 * Structure: one divider clk -> tick_env (CLK_HZ/128 cycles apart), then a
 * 7-bit counter of env ticks -> tick_poll every 128th tick_env, so the two
 * strobes are exactly ratio-locked (tick_poll coincides with a tick_env).
 * With CLK_HZ not divisible by 128 (e.g. the nominal 1 MHz RC: 1e6/128 =
 * 7812 -> 128.008 Hz) the env rate carries the integer-divide remainder --
 * irrelevant against the on-die RC oscillator's own tolerance.
 *
 * Verilog-2001, single clock, synchronous reset, no latches, strobes 1 clk.
 */
module clkdiv #(parameter CLK_HZ = 1000000) (
    input  wire clk, input wire rst_n,
    output reg  tick_env,   // 128 Hz, 1-cycle strobe: envelope + settle timing
    output reg  tick_poll   // 1 Hz, 1-cycle strobe: the poll cadence (main.c's PIT)
);

    localparam integer ENV_DIV = CLK_HZ / 128;   // clk cycles per tick_env

    // constant fn (Verilog-2001) so the counter is sized, not a blanket 32 bits
    function integer clog2 (input integer value);
        integer v;
        begin
            v = value - 1;
            for (clog2 = 0; v > 0; clog2 = clog2 + 1)
                v = v >> 1;
        end
    endfunction

    localparam integer ENV_W = (ENV_DIV < 2) ? 1 : clog2(ENV_DIV);

    reg [ENV_W-1:0] env_cnt;      // 0 .. ENV_DIV-1
    reg [6:0]       env_of_poll;  // 0 .. 127 tick_envs per tick_poll

    always @(posedge clk) begin
        if (!rst_n) begin
            env_cnt     <= {ENV_W{1'b0}};
            env_of_poll <= 7'd0;
            tick_env    <= 1'b0;
            tick_poll   <= 1'b0;
        end else begin
            tick_env  <= 1'b0;                    // default: strobes are 1 clk wide
            tick_poll <= 1'b0;
            if (env_cnt == ENV_DIV - 1) begin
                env_cnt  <= {ENV_W{1'b0}};
                tick_env <= 1'b1;
                if (env_of_poll == 7'd127) begin
                    env_of_poll <= 7'd0;
                    tick_poll   <= 1'b1;          // every 128th env tick = 1 Hz
                end else begin
                    env_of_poll <= env_of_poll + 7'd1;
                end
            end else begin
                env_cnt <= env_cnt + {{(ENV_W-1){1'b0}}, 1'b1};
            end
        end
    end

endmodule
