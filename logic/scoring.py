def chicago_score(contract_level, contract_suit, doubled, declarer_vulnerable, tricks_made):
    
    """
    Calculates the score breakdown for a Chicago Bridge game.
    
    Args:
        contract_level (int): Level of the contract (1-7)
        contract_suit (str): Suit of the contract ('clubs', 'diamonds', 'hearts', 'spades', 'notrump')
        doubled (str): Doubling status ('', 'X', 'XX')
        declarer_vulnerable (bool): Whether the declarer is vulnerable
        tricks_made (int): Number of tricks made
        
    Returns:
        dict: Breakdown of the score components
    """
    
    # Base values for suits and multipliers
    suit_points = {'clubs': 20, 'diamonds': 20, 'hearts': 30, 'spades': 30, 'notrump': 30}
    doubling_multiplier = {'': 1, 'X': 2, 'XX': 4}
    
    # Basic calculation variables
    base_score = suit_points[contract_suit]
    multiplier = doubling_multiplier[doubled]
    required_tricks = 6 + contract_level
    overtricks = tricks_made - required_tricks
    
    # Initialize result dictionary
    result = {
        'contract_points': 0,
        'overtricks': 0,
        'bonuses': 0,
        'insult_bonus': 0,
        'slam_bonus': 0,
        'game_bonus': 0,
        'part_score_bonus': 0,
        'penalty': 0,
        'total': 0
    }
    
    # Contract made or exceeded
    if overtricks >= 0:
        # Base points for the contract
        first_trick_bonus = 10 if contract_suit == 'notrump' else 0
        result['contract_points'] = contract_level * base_score * multiplier + first_trick_bonus * multiplier
        
        # Overtricks
        if doubled == '':
            result['overtricks'] = overtricks * base_score
        elif doubled == 'X':
            result['overtricks'] = overtricks * (200 if declarer_vulnerable else 100)
        else:  # redoubled
            result['overtricks'] = overtricks * (400 if declarer_vulnerable else 200)
        
        # Game/Part-score Bonus
        if result['contract_points'] < 100:
            result['part_score_bonus'] = 50
        else:
            result['game_bonus'] = 500 if declarer_vulnerable else 300
        
        # Slam bonus
        if contract_level == 6:
            result['slam_bonus'] = 750 if declarer_vulnerable else 500
        elif contract_level == 7:
            result['slam_bonus'] = 1500 if declarer_vulnerable else 1000
        
        # Insult bonus (for making doubled/redoubled contracts)
        if doubled == 'X':
            result['insult_bonus'] = 50
        elif doubled == 'XX':
            result['insult_bonus'] = 100
    
    # Contract down
    else:
        # Calculate penalties for contracts that went down
        down = abs(overtricks)
        
        if doubled == '':
            # Not doubled: 50 (not vulnerable) or 100 (vulnerable) per undertrick
            result['penalty'] = -down * (100 if declarer_vulnerable else 50)
        else:
            # Doubled or redoubled
            penalty = 0
            
            if declarer_vulnerable:
                # Vulnerable: 200, 300, 300, ...
                penalty = 200 + (down - 1) * 300
            else:
                # Not vulnerable: 100, 200, 200, ...
                if down == 1:
                    penalty = 100
                else:
                    penalty = 100 + (down - 1) * 200
            
            # Redoubled doubles the penalty again
            penalty *= 2 if doubled == 'XX' else 1
            result['penalty'] = -penalty
    
    # Calculate total bonus points
    result['bonuses'] = (
        result['part_score_bonus'] +
        result['game_bonus'] +
        result['slam_bonus'] +
        result['insult_bonus']
    )
    
    # Calculate total score
    result['total'] = result['contract_points'] + result['overtricks'] + result['bonuses'] + result['penalty']
    
    return result