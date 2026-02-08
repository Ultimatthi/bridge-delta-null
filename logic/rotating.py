def chicago_rotate(round_number):
    
    """
    Determines dealer and vulnerability according to the extended Chicago rotation system.
    
    Args:
        round_number (int): Positive round number (starting form 0)
        
    Returns:
        Tuple of (dealer, vulnerability)
    """
    
    dealer_seq = ["north", "east", "south", "west"]
    vulnerability_seq = ["none", "northsouth", "eastwest", "both"]
    
    # Calculate block and position within the block
    block = round_number // 4 % 4
    position = round_number % 4
    
    # Determine dealer and vulnerability
    dealer = dealer_seq[position]
    vulnerability = vulnerability_seq[(block + position) % 4]
    
    return dealer, vulnerability