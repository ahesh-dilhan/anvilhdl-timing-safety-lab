// SPDX-License-Identifier: MIT
//
// Correct implementation: the request address remains unchanged from request
// acceptance through the variable-latency response event.

`timescale 1ns/1ps

module safe_dynamic_memory_client #(
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

    typedef enum logic {
        SEND_REQUEST,
        WAIT_FOR_RESPONSE
    } client_state_t;

    client_state_t state;
    logic [COUNT_WIDTH-1:0] completed_count;

    // rsp_data is intentionally unused here.  The common scoreboard performs
    // the same functional check for both clients.
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
                        state     <= WAIT_FOR_RESPONSE;
                    end
                end

                WAIT_FOR_RESPONSE: begin
                    if (rsp_valid) begin
                        // Mutation is now safe: the response event ended the
                        // outstanding request's loan interval.
                        req_addr        <= req_addr + ADDRESS_STEP;
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
