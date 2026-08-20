// SPDX-License-Identifier: MIT
//
// Intentionally unsafe: after request acceptance, this client assumes the
// address loan lasts exactly one cycle.  It therefore happens to work for a
// one-cycle response and violates the interface for every longer response.

`timescale 1ns/1ps

module unsafe_dynamic_memory_client #(
    parameter integer NUM_TRANSACTIONS = 6,
    parameter logic [7:0] START_ADDRESS = 8'h10,
    parameter logic [7:0] ADDRESS_STEP  = 8'h13
) (
    input  logic       clk,
    input  logic       rst_n,

    output logic       req_valid,
    input  logic       req_ready,
    output logic [7:0] req_addr,

    input  logic       rsp_valid,
    input  logic [7:0] rsp_data,

    output logic       done
);

    localparam integer COUNT_WIDTH = $clog2(NUM_TRANSACTIONS + 1);

    typedef enum logic [1:0] {
        SEND_REQUEST,
        ASSUMED_ONE_CYCLE_LOAN,
        WAIT_FOR_RESPONSE
    } client_state_t;

    client_state_t state;
    logic [COUNT_WIDTH-1:0] completed_count;

    // rsp_data is intentionally unused here.  Functional checking belongs to
    // the common testbench so the safe and unsafe clients face identical logic.
    logic unused_rsp_data;
    assign unused_rsp_data = ^rsp_data;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state           <= SEND_REQUEST;
            req_valid       <= 1'b0;
            req_addr        <= START_ADDRESS;
            completed_count <= '0;
            done            <= 1'b0;
        end else begin
            case (state)
                SEND_REQUEST: begin
                    req_valid <= 1'b1;
                    if (req_valid && req_ready) begin
                        req_valid <= 1'b0;
                        state     <= ASSUMED_ONE_CYCLE_LOAN;
                    end
                end

                ASSUMED_ONE_CYCLE_LOAN: begin
                    // The bug: a fixed one-cycle assumption replaces waiting
                    // for the dynamic response event.
                    req_addr <= req_addr + ADDRESS_STEP;
                    if (rsp_valid) begin
                        completed_count <= completed_count + 1'b1;
                        if (completed_count == NUM_TRANSACTIONS - 1) begin
                            done <= 1'b1;
                        end else begin
                            req_valid <= 1'b1;
                            state     <= SEND_REQUEST;
                        end
                    end else begin
                        state <= WAIT_FOR_RESPONSE;
                    end
                end

                WAIT_FOR_RESPONSE: begin
                    if (rsp_valid) begin
                        completed_count <= completed_count + 1'b1;
                        if (completed_count == NUM_TRANSACTIONS - 1) begin
                            done <= 1'b1;
                        end else begin
                            req_valid <= 1'b1;
                            state     <= SEND_REQUEST;
                        end
                    end
                end

                default: begin
                    state     <= SEND_REQUEST;
                    req_valid <= 1'b0;
                end
            endcase
        end
    end

endmodule
