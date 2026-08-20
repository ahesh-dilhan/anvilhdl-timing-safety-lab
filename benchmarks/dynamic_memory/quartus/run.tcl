package require ::quartus::project
package require ::quartus::flow

proc usage {} {
    puts stderr "Usage: quartus_sh -t run.tcl --variant NAME --top MODULE --rtl FILE ?--rtl FILE ...? ?--build-dir DIR? ?--sdc FILE?"
    puts stderr ""
    puts stderr "The flow is pinned to Cyclone IV E EP4CE115F29C7, seed 1, and the"
    puts stderr "tracked 20 ns constraint unless --sdc is supplied. Testbench and"
    puts stderr "memory-model files must not be passed as synthesis sources."
}

set script_dir [file normalize [file dirname [info script]]]
set invocation_dir [pwd]
set variant ""
set top ""
set rtl_files {}
set build_dir ""
set sdc_file [file join $script_dir constraints.sdc]

set index 0
while {$index < [llength $argv]} {
    set option [lindex $argv $index]
    incr index

    switch -- $option {
        --variant - --top - --rtl - --build-dir - --sdc {
            if {$index >= [llength $argv]} {
                puts stderr "ERROR: $option requires a value"
                usage
                exit 2
            }
            set value [lindex $argv $index]
            incr index

            switch -- $option {
                --variant { set variant $value }
                --top { set top $value }
                --rtl { lappend rtl_files [file normalize [file join $invocation_dir $value]] }
                --build-dir { set build_dir [file normalize [file join $invocation_dir $value]] }
                --sdc { set sdc_file [file normalize [file join $invocation_dir $value]] }
            }
        }
        --help - -h {
            usage
            exit 0
        }
        default {
            puts stderr "ERROR: unknown option '$option'"
            usage
            exit 2
        }
    }
}

if {$variant eq "" || $top eq "" || [llength $rtl_files] == 0} {
    puts stderr "ERROR: --variant, --top, and at least one --rtl are required"
    usage
    exit 2
}
if {![regexp {^[A-Za-z0-9_-]+$} $variant]} {
    puts stderr "ERROR: variant may contain only letters, digits, underscores, and hyphens"
    exit 2
}
if {![regexp {^[A-Za-z_][A-Za-z0-9_$]*$} $top]} {
    puts stderr "ERROR: '$top' is not a valid SystemVerilog module name"
    exit 2
}
if {$build_dir eq ""} {
    set build_dir [file join $script_dir build $variant]
}
if {![file isfile $sdc_file]} {
    puts stderr "ERROR: SDC file does not exist: $sdc_file"
    exit 2
}
foreach rtl_file $rtl_files {
    if {![file isfile $rtl_file]} {
        puts stderr "ERROR: RTL source does not exist: $rtl_file"
        exit 2
    }
}

set project_suffix [string map {- _} $variant]
set project_name "dynamic_memory_${project_suffix}"
file mkdir $build_dir
cd $build_dir

puts "INFO: variant=$variant"
puts "INFO: project=$project_name"
puts "INFO: top=$top"
puts "INFO: build_dir=$build_dir"
puts "INFO: device=EP4CE115F29C7"
puts "INFO: constraint=$sdc_file"
foreach rtl_file $rtl_files {
    puts "INFO: rtl=$rtl_file"
}

project_new $project_name -overwrite
set_global_assignment -name FAMILY "Cyclone IV E"
set_global_assignment -name DEVICE EP4CE115F29C7
set_global_assignment -name TOP_LEVEL_ENTITY $top
set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files
set_global_assignment -name NUM_PARALLEL_PROCESSORS 2
set_global_assignment -name SEED 1
set_global_assignment -name SDC_FILE $sdc_file
foreach rtl_file $rtl_files {
    set extension [string tolower [file extension $rtl_file]]
    if {$extension eq ".sv" || $extension eq ".svh"} {
        set_global_assignment -name SYSTEMVERILOG_FILE $rtl_file
    } else {
        set_global_assignment -name VERILOG_FILE $rtl_file
    }
}
export_assignments

set flow_result [catch {execute_flow -compile} flow_message flow_options]
project_close
if {$flow_result != 0} {
    puts stderr "ERROR: Quartus compilation failed: $flow_message"
    exit 1
}

puts "INFO: Quartus compilation completed successfully"
puts "INFO: collect results with:"
puts "INFO: python3 [file join $script_dir collect_results.py] $build_dir"
