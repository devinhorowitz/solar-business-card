/*
 * sar_ctrl.v -- DRH-1 companion ASIC: 8-bit SAR A/D conversion control
 *               (SPEC.md port contract -- do not deviate).
 *
 * Firmware mirror: firmware/sense.c, adc_read_raw(). On the card the
 * AVR64EA28's ADC0 is itself a SAR engine that the firmware powers up for
 * exactly one conversion and shuts back down (LOWLAT = 0, ENABLE pulsed per
 * read). Here the successive-approximation register is explicit RTL; the
 * analog half (R-2R DAC + comparator + reference) is a stub outside this
 * module BY DESIGN, per SPEC. One `go` = one conversion = the firmware's one
 * ADC_MODE_SINGLE / START_IMMEDIATE read, at 8 bits instead of 12.
 *
 * Search: MSB-first binary search, 2 clk per bit (set + settle cycle, then
 * sample cycle) = 16 clk per conversion. `done` is a 1-cycle strobe; `result`
 * holds until the next conversion completes. `go` is ignored while busy.
 *
 * Comparator convention (SPEC): cmp_in = 1 when Vin > DAC(dac_code) --
 * STRICTLY greater. A SAR that drives the trial code T itself and keeps the
 * bit on cmp_in converges to Vin-1 under that ideal integer comparator. So
 * the DAC is driven at T-1 (the DAC string sitting half an LSB low -- the
 * standard SAR DAC offset): cmp_in then evaluates (Vin > T-1) == (Vin >= T),
 * and the search converges to Vin EXACTLY over the full 0..255 range. T
 * always has its trial bit set, so T >= 1 and T-1 never underflows.
 *
 * Verilog-2001, single clock, synchronous reset (rst_n sampled on posedge
 * clk), no latches, no initial blocks, strobes exactly 1 clk wide.
 */
module sar_ctrl (
    input  wire clk, input wire rst_n, input wire go,
    input  wire cmp_in,                  // analog comparator: 1 when Vin > DAC(dac_code)
    output reg  [7:0] dac_code,
    output reg  [7:0] result, output reg done, output reg busy
);

    reg [7:0] acc;     // bits kept so far (MSB-first accumulation)
    reg [2:0] idx;     // trial bit index, 7 down to 0
    reg       phase;   // 0 = code just set (settle cycle), 1 = sample cmp_in

    // acc after sampling bit `idx`: keep the trial bit iff Vin >= trial
    wire [7:0] kept = cmp_in ? (acc | (8'h01 << idx)) : acc;

    always @(posedge clk) begin
        if (!rst_n) begin
            dac_code <= 8'd0;
            result   <= 8'd0;
            done     <= 1'b0;
            busy     <= 1'b0;
            acc      <= 8'd0;
            idx      <= 3'd0;
            phase    <= 1'b0;
        end else begin
            done <= 1'b0;                          // 1-cycle strobe
            if (!busy) begin
                if (go) begin                      // accept one conversion
                    busy     <= 1'b1;
                    acc      <= 8'd0;
                    idx      <= 3'd7;
                    dac_code <= 8'h7F;             // trial 0x80, driven one LSB low
                    phase    <= 1'b0;
                end
            end else if (!phase) begin
                phase <= 1'b1;                     // settle: DAC + comparator slew
            end else begin                         // sample cmp_in this edge
                phase <= 1'b0;
                if (idx == 3'd0) begin             // bit 0 decided: conversion over
                    result <= kept;
                    done   <= 1'b1;
                    busy   <= 1'b0;
                end else begin                     // set the next trial code
                    acc      <= kept;
                    idx      <= idx - 3'd1;
                    dac_code <= (kept | (8'h01 << (idx - 3'd1))) - 8'd1;
                end
            end
        end
    end

endmodule
