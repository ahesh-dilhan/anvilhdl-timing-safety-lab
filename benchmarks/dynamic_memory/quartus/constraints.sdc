# Common constraint for every dynamic-memory-client variant.
#
# This intentionally constrains only the internal register-to-register paths.
# It is suitable for a small, controlled comparison, not board timing sign-off.
create_clock -name dynamic_memory_clk -period 20.000 [get_ports {clk}]
derive_clock_uncertainty
