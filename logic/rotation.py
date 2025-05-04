def chicago_rotate(round_number):
    
    """
    Determines dealer and vulnerability according to the extended Chicago rotation system.
    After every 4-round block, the dealer skips a position in the rotation order.
    
    Args:
        round_number: Positive round number (minimum 1)
        
    Returns:
        Tuple of (dealer, vulnerability)
    """
    
    dealer_order = ["north", "east", "south", "west"]
    
    # Calculate block and position within the block
    index = round_number - 1
    block_start = index // 4 % 4
    position = index % 4
    
    # Determine dealer
    dealer_index = (block_start + position) % 4
    dealer = dealer_order[dealer_index]
    
    # Vulnerability based on position within the block
    if position == 0:
        vulnerability = "none"
    elif position == 3:
        vulnerability = "both"
    else:
        vulnerability = "northsouth" if dealer in ["north", "south"] else "eastwest"
    
    return dealer, vulnerability