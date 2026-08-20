// SPDX-License-Identifier: MIT

`timescale 1ns/1ps

module tb_dynamic_memory;

    localparam integer NUM_TRANSACTIONS = 6;
    localparam integer EXPECTED_UNSAFE_FAILURES = 4;

    logic clk;
    logic rst_n;

    logic       unsafe_req_valid;
    logic       unsafe_req_ready;
    logic [7:0] unsafe_req_addr;
    logic       unsafe_rsp_valid;
    logic [7:0] unsafe_rsp_data;
    logic       unsafe_busy;
    logic [3:0] unsafe_active_latency;
    logic       unsafe_done;

    logic       safe_req_valid;
    logic       safe_req_ready;
    logic [7:0] safe_req_addr;
    logic       safe_rsp_valid;
    logic [7:0] safe_rsp_data;
    logic       safe_busy;
    logic [3:0] safe_active_latency;
    logic       safe_done;

    integer cycle_count;
    integer unsafe_request_count;
    integer unsafe_response_count;
    integer unsafe_mismatch_count;
    integer unsafe_stability_violation_count;
    integer unsafe_sequence_error_count;
    integer unsafe_first_failure_cycle;
    integer safe_request_count;
    integer safe_response_count;
    integer safe_mismatch_count;
    integer safe_stability_violation_count;
    integer safe_sequence_error_count;
    integer schedule_divergence_count;

    logic       unsafe_outstanding;
    logic [7:0] unsafe_loan_address;
    logic [7:0] unsafe_expected_data;
    logic [3:0] unsafe_loan_latency;
    logic       unsafe_violation_seen;

    logic       safe_outstanding;
    logic [7:0] safe_loan_address;
    logic [7:0] safe_expected_data;
    logic [3:0] safe_loan_latency;
    logic       safe_violation_seen;

    string      vcd_path;

    function automatic logic [7:0] data_for_address(input logic [7:0] address);
        data_for_address = {address[6:0], address[7]} ^ 8'hA5;
    endfunction

    function automatic logic [7:0] expected_address(input integer index);
        expected_address = 8'h10 + (index * 8'h13);
    endfunction

    function automatic logic [3:0] expected_latency(input integer index);
        case (index)
            0: expected_latency = 4'd1;
            1: expected_latency = 4'd2;
            2: expected_latency = 4'd3;
            3: expected_latency = 4'd4;
            4: expected_latency = 4'd1;
            5: expected_latency = 4'd4;
            default: expected_latency = 4'd1;
        endcase
    endfunction

    unsafe_dynamic_memory_client #(
        .NUM_TRANSACTIONS(NUM_TRANSACTIONS)
    ) unsafe_client (
        .clk,
        .rst_n,
        .req_valid(unsafe_req_valid),
        .req_ready(unsafe_req_ready),
        .req_addr(unsafe_req_addr),
        .rsp_valid(unsafe_rsp_valid),
        .rsp_data(unsafe_rsp_data),
        .done(unsafe_done)
    );

    variable_latency_memory unsafe_memory (
        .clk,
        .rst_n,
        .req_valid(unsafe_req_valid),
        .req_ready(unsafe_req_ready),
        .req_addr(unsafe_req_addr),
        .rsp_valid(unsafe_rsp_valid),
        .rsp_data(unsafe_rsp_data),
        .busy(unsafe_busy),
        .active_latency(unsafe_active_latency)
    );

    safe_dynamic_memory_client #(
        .NUM_TRANSACTIONS(NUM_TRANSACTIONS)
    ) safe_client (
        .clk,
        .rst_n,
        .req_valid(safe_req_valid),
        .req_ready(safe_req_ready),
        .req_addr(safe_req_addr),
        .rsp_valid(safe_rsp_valid),
        .rsp_data(safe_rsp_data),
        .done(safe_done)
    );

    variable_latency_memory safe_memory (
        .clk,
        .rst_n,
        .req_valid(safe_req_valid),
        .req_ready(safe_req_ready),
        .req_addr(safe_req_addr),
        .rsp_valid(safe_rsp_valid),
        .rsp_data(safe_rsp_data),
        .busy(safe_busy),
        .active_latency(safe_active_latency)
    );

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    initial begin
        rst_n = 1'b0;
        repeat (4) @(posedge clk);
        rst_n <= 1'b1;
    end

    initial begin
        if (!$value$plusargs("VCD=%s", vcd_path))
            vcd_path = "generated/dynamic_memory.vcd";
        $dumpfile(vcd_path);
        $dumpvars(0, tb_dynamic_memory);
    end

    // The two monitors intentionally use the same checks.  Their only
    // expected difference is whether req_addr remains equal to loan_address
    // until rsp_valid ends the outstanding interval.
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cycle_count                     <= 0;
            unsafe_request_count            <= 0;
            unsafe_response_count           <= 0;
            unsafe_mismatch_count           <= 0;
            unsafe_stability_violation_count <= 0;
            unsafe_sequence_error_count     <= 0;
            unsafe_first_failure_cycle      <= -1;
            unsafe_outstanding              <= 1'b0;
            unsafe_loan_address             <= 8'h00;
            unsafe_expected_data            <= 8'h00;
            unsafe_loan_latency             <= 4'd0;
            unsafe_violation_seen           <= 1'b0;
            safe_request_count              <= 0;
            safe_response_count             <= 0;
            safe_mismatch_count             <= 0;
            safe_stability_violation_count  <= 0;
            safe_sequence_error_count       <= 0;
            safe_outstanding                <= 1'b0;
            safe_loan_address               <= 8'h00;
            safe_expected_data              <= 8'h00;
            safe_loan_latency               <= 4'd0;
            safe_violation_seen             <= 1'b0;
            schedule_divergence_count       <= 0;
        end else begin
            cycle_count <= cycle_count + 1;

            // Both implementations must receive requests and responses on the
            // same cycles, ensuring a genuinely identical latency experiment.
            if ((unsafe_req_valid && unsafe_req_ready) !=
                (safe_req_valid && safe_req_ready)) begin
                schedule_divergence_count <= schedule_divergence_count + 1;
                $display("ERROR kind=schedule_divergence phase=request cycle=%0d", cycle_count);
            end
            if (unsafe_rsp_valid != safe_rsp_valid) begin
                schedule_divergence_count <= schedule_divergence_count + 1;
                $display("ERROR kind=schedule_divergence phase=response cycle=%0d", cycle_count);
            end

            if (unsafe_req_valid && unsafe_req_ready) begin
                if (unsafe_outstanding) begin
                    unsafe_sequence_error_count <= unsafe_sequence_error_count + 1;
                    $display("ERROR implementation=unsafe kind=overlapping_request cycle=%0d", cycle_count);
                end
                if (unsafe_req_addr !== expected_address(unsafe_request_count)) begin
                    unsafe_sequence_error_count <= unsafe_sequence_error_count + 1;
                    $display("ERROR implementation=unsafe kind=request_sequence transaction=%0d expected_addr=0x%02h observed_addr=0x%02h",
                             unsafe_request_count, expected_address(unsafe_request_count), unsafe_req_addr);
                end
                unsafe_outstanding    <= 1'b1;
                unsafe_loan_address   <= unsafe_req_addr;
                unsafe_expected_data  <= data_for_address(unsafe_req_addr);
                unsafe_loan_latency   <= expected_latency(unsafe_request_count);
                unsafe_violation_seen <= 1'b0;
                unsafe_request_count  <= unsafe_request_count + 1;
            end

            if (unsafe_outstanding) begin
                // Sample the borrowed value at the response edge too.  A
                // mutation scheduled on that edge is allowed (NBA update
                // occurs afterwards), but an earlier mutation is already
                // visible here and must not be hidden by rsp_valid.
                if ((unsafe_req_addr !== unsafe_loan_address) &&
                    !unsafe_violation_seen) begin
                    unsafe_stability_violation_count <= unsafe_stability_violation_count + 1;
                    unsafe_violation_seen <= 1'b1;
                    if (unsafe_first_failure_cycle < 0)
                        unsafe_first_failure_cycle <= cycle_count;
                    $display("EVENT implementation=unsafe kind=stability_violation transaction=%0d latency=%0d cycle=%0d loaned_addr=0x%02h observed_addr=0x%02h",
                             unsafe_response_count, unsafe_loan_latency, cycle_count,
                             unsafe_loan_address, unsafe_req_addr);
                end
                if (unsafe_rsp_valid) begin
                    unsafe_outstanding    <= 1'b0;
                    unsafe_response_count <= unsafe_response_count + 1;
                    if (unsafe_rsp_data !== unsafe_expected_data) begin
                        unsafe_mismatch_count <= unsafe_mismatch_count + 1;
                        $display("EVENT implementation=unsafe kind=data_mismatch transaction=%0d latency=%0d cycle=%0d expected=0x%02h observed=0x%02h",
                                 unsafe_response_count, unsafe_loan_latency, cycle_count,
                                 unsafe_expected_data, unsafe_rsp_data);
                    end else begin
                        $display("EVENT implementation=unsafe kind=transaction_pass transaction=%0d latency=%0d cycle=%0d",
                                 unsafe_response_count, unsafe_loan_latency, cycle_count);
                    end
                end
            end

            if (safe_req_valid && safe_req_ready) begin
                if (safe_outstanding) begin
                    safe_sequence_error_count <= safe_sequence_error_count + 1;
                    $display("ERROR implementation=safe kind=overlapping_request cycle=%0d", cycle_count);
                end
                if (safe_req_addr !== expected_address(safe_request_count)) begin
                    safe_sequence_error_count <= safe_sequence_error_count + 1;
                    $display("ERROR implementation=safe kind=request_sequence transaction=%0d expected_addr=0x%02h observed_addr=0x%02h",
                             safe_request_count, expected_address(safe_request_count), safe_req_addr);
                end
                safe_outstanding    <= 1'b1;
                safe_loan_address   <= safe_req_addr;
                safe_expected_data  <= data_for_address(safe_req_addr);
                safe_loan_latency   <= expected_latency(safe_request_count);
                safe_violation_seen <= 1'b0;
                safe_request_count  <= safe_request_count + 1;
            end

            if (safe_outstanding) begin
                if ((safe_req_addr !== safe_loan_address) &&
                    !safe_violation_seen) begin
                    safe_stability_violation_count <= safe_stability_violation_count + 1;
                    safe_violation_seen <= 1'b1;
                    $display("ERROR implementation=safe kind=stability_violation transaction=%0d latency=%0d cycle=%0d loaned_addr=0x%02h observed_addr=0x%02h",
                             safe_response_count, safe_loan_latency, cycle_count,
                             safe_loan_address, safe_req_addr);
                end
                if (safe_rsp_valid) begin
                    safe_outstanding    <= 1'b0;
                    safe_response_count <= safe_response_count + 1;
                    if (safe_rsp_data !== safe_expected_data) begin
                        safe_mismatch_count <= safe_mismatch_count + 1;
                        $display("ERROR implementation=safe kind=data_mismatch transaction=%0d latency=%0d cycle=%0d expected=0x%02h observed=0x%02h",
                                 safe_response_count, safe_loan_latency, cycle_count,
                                 safe_expected_data, safe_rsp_data);
                    end else begin
                        $display("EVENT implementation=safe kind=transaction_pass transaction=%0d latency=%0d cycle=%0d",
                                 safe_response_count, safe_loan_latency, cycle_count);
                    end
                end
            end
        end
    end

    initial begin : result_and_timeout
        fork
            begin : run_to_completion
                wait (safe_done && unsafe_done);
                @(posedge clk);
                #1;

                $display("RESULT benchmark=dynamic_memory implementation=unsafe status=EXPECTED_FAILURE transactions=%0d mismatches=%0d stability_violations=%0d first_failure_cycle=%0d",
                         unsafe_response_count, unsafe_mismatch_count,
                         unsafe_stability_violation_count, unsafe_first_failure_cycle);
                $display("RESULT benchmark=dynamic_memory implementation=safe status=%s transactions=%0d mismatches=%0d stability_violations=%0d",
                         ((safe_mismatch_count == 0) &&
                          (safe_stability_violation_count == 0)) ? "PASS" : "FAIL",
                         safe_response_count, safe_mismatch_count,
                         safe_stability_violation_count);

                if ((unsafe_request_count != NUM_TRANSACTIONS) ||
                    (unsafe_response_count != NUM_TRANSACTIONS) ||
                    (unsafe_mismatch_count != EXPECTED_UNSAFE_FAILURES) ||
                    (unsafe_stability_violation_count != EXPECTED_UNSAFE_FAILURES) ||
                    (unsafe_sequence_error_count != 0) ||
                    (safe_request_count != NUM_TRANSACTIONS) ||
                    (safe_response_count != NUM_TRANSACTIONS) ||
                    (safe_mismatch_count != 0) ||
                    (safe_stability_violation_count != 0) ||
                    (safe_sequence_error_count != 0) ||
                    (schedule_divergence_count != 0)) begin
                    $display("RESULT benchmark=dynamic_memory status=FAIL expected_unsafe_failures=%0d schedule_divergences=%0d",
                             EXPECTED_UNSAFE_FAILURES, schedule_divergence_count);
                    $fatal(1, "dynamic-memory benchmark did not match its expected outcomes");
                end

                $display("RESULT benchmark=dynamic_memory status=PASS expected_unsafe_failures=%0d schedule_divergences=%0d",
                         EXPECTED_UNSAFE_FAILURES, schedule_divergence_count);
                $finish;
            end

            begin : timeout_guard
                repeat (200) @(posedge clk);
                $display("RESULT benchmark=dynamic_memory status=FAIL reason=timeout safe_done=%0d unsafe_done=%0d",
                         safe_done, unsafe_done);
                $fatal(1, "dynamic-memory benchmark timeout");
            end
        join_any
        disable fork;
    end

endmodule
