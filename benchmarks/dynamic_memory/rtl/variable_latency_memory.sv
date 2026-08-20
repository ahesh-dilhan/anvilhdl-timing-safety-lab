// SPDX-License-Identifier: MIT
//
// A deliberately small model of a memory interface whose request address is
// borrowed until the response.  The model acknowledges a request immediately,
// but reads the live request address only when the selected response event
// occurs.  A client must therefore keep req_addr stable while the request is
// outstanding, even though req_valid may be deasserted after acceptance.

`timescale 1ns/1ps

module variable_latency_memory (
    input  logic       clk,
    input  logic       rst_n,

    input  logic       req_valid,
    output logic       req_ready,
    input  logic [7:0] req_addr,

    output logic       rsp_valid,
    output logic [7:0] rsp_data,

    output logic       busy,
    output logic [3:0] active_latency
);

    logic [3:0] remaining_cycles;
    logic [2:0] transaction_index;

    // The six transactions use the deterministic latency vector
    // [1, 2, 3, 4, 1, 4].  The default makes the model reusable if a client
    // accidentally sends more than six requests.
    function automatic logic [3:0] latency_for_transaction(
        input logic [2:0] index
    );
        case (index)
            3'd0: latency_for_transaction = 4'd1;
            3'd1: latency_for_transaction = 4'd2;
            3'd2: latency_for_transaction = 4'd3;
            3'd3: latency_for_transaction = 4'd4;
            3'd4: latency_for_transaction = 4'd1;
            3'd5: latency_for_transaction = 4'd4;
            default: latency_for_transaction = 4'd1;
        endcase
    endfunction

    // A bijective address-to-data mapping makes every premature address
    // change observable by the scoreboard without needing a large memory.
    function automatic logic [7:0] data_for_address(input logic [7:0] address);
        data_for_address = {address[6:0], address[7]} ^ 8'hA5;
    endfunction

    assign req_ready = !busy;

    // The response event is the clock edge for which one cycle remains.  Data
    // is meaningful at that edge and is derived from the still-borrowed live
    // address.  This makes a configured latency of one exactly one clock from
    // request acceptance to response completion, with no extra registered-
    // valid cycle hidden in the model.
    assign rsp_valid = busy && (remaining_cycles == 4'd1);
    assign rsp_data  = data_for_address(req_addr);

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy             <= 1'b0;
            active_latency   <= 4'd0;
            remaining_cycles <= 4'd0;
            transaction_index <= 3'd0;
        end else begin
            if (!busy) begin
                if (req_valid && req_ready) begin
                    busy              <= 1'b1;
                    active_latency    <= latency_for_transaction(transaction_index);
                    remaining_cycles  <= latency_for_transaction(transaction_index);
                    transaction_index <= transaction_index + 3'd1;
                end
            end else if (remaining_cycles == 4'd1) begin
                // The protocol intentionally permits the memory to use the
                // borrowed address at this dynamic response boundary.
                busy             <= 1'b0;
                remaining_cycles <= 4'd0;
            end else begin
                remaining_cycles <= remaining_cycles - 4'd1;
            end
        end
    end

endmodule
