# DRH-1 companion ASIC -- simulation + size gate (SPEC.md "Verification
# floor" / "Size gate"). Everything here runs on stock Icarus + yosys, the
# "no external tools beyond what installs in the CI container" rule.
#
#   make sim     run every self-checking testbench (tb/tb_*.v); a TB passes
#                only if it prints "TB PASS" AND vvp exits clean ($fatal
#                makes it exit non-zero). Stops on the first failure.
#   make synth   yosys generic synth of drh1_top -> synth_stat.txt
#   make gates   same, then abc -g NAND for the NAND2-equivalent count
#                (SPEC's quarter-slot sizing) -> synth_nand.txt
#
# tb/i2c_slave_model.v is a behavioural bus model REUSED by testbenches, not
# a testbench itself -- it is compiled into every TB build, never run alone.

RTL    := $(wildcard rtl/*.v)
MODELS := tb/i2c_slave_model.v
TBS    := $(wildcard tb/tb_*.v)

BUILD  := build

.PHONY: sim synth gates clean

sim:
	@mkdir -p $(BUILD)
	@set -e; \
	for tb in $(TBS); do \
	    name=$$(basename $$tb .v); \
	    echo "==== $$name"; \
	    iverilog -g2012 -s $$name -o $(BUILD)/$$name.vvp $(RTL) $(MODELS) $$tb; \
	    vvp $(BUILD)/$$name.vvp > $(BUILD)/$$name.log 2>&1 \
	        || { cat $(BUILD)/$$name.log; echo "FAIL: $$name (vvp exit)"; exit 1; }; \
	    cat $(BUILD)/$$name.log; \
	    grep -q "TB PASS" $(BUILD)/$$name.log \
	        || { echo "FAIL: $$name (no TB PASS line)"; exit 1; }; \
	done; \
	echo "==== ALL TB PASS"

synth:
	yosys -p "read_verilog $(RTL); hierarchy -top drh1_top; synth; stat" | tee synth_stat.txt

gates:
	yosys -p "read_verilog $(RTL); hierarchy -top drh1_top; synth; abc -g NAND; stat" | tee synth_nand.txt

clean:
	rm -rf $(BUILD) synth_stat.txt synth_nand.txt
