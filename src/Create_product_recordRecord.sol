
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Create_product_recordRecord {
    string public product_id;
    string public product_name;
    int256 public price;
    bool public is_available;

    constructor(string memory _product_id, string memory _product_name, int256 _price, bool _is_available) {
        product_id = _product_id;
        product_name = _product_name;
        price = _price;
        is_available = _is_available;
    }
}
