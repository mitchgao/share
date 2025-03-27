WITH RankedTrades AS (
    SELECT 
        n.account_number,
        n.transaction_id AS trade_id,
        n.security_id AS trade_security,
        n.amount AS trade_amount,
        n.trade_date,
        r.transaction_id AS redemption_id,
        r.redemption_date,
        ROW_NUMBER() OVER (
            PARTITION BY n.account_number, n.transaction_id 
            ORDER BY r.redemption_date ASC
        ) AS rn  -- Assign each trade to the earliest redemption within 30 days
    FROM redemption_position r
    JOIN new_trade n 
        ON r.account_number = n.account_number  
        AND n.trade_date BETWEEN r.redemption_date AND DATEADD(DAY, 30, r.redemption_date)
)
SELECT 
    r.account_number,
    r.transaction_id AS redemption_id,
    r.security_id AS redemption_security,
    r.amount AS redemption_amount,
    r.redemption_date,
    
    -- Concatenated Trade IDs
    STRING_AGG(n.trade_id, ', ') AS grouped_trade_ids,
    
    -- Concatenated Security IDs
    STRING_AGG(n.trade_security, ', ') AS grouped_security_ids,

    -- Concatenated Trade IDs with Amounts (e.g., T1(500), T2(1500))
    STRING_AGG(n.trade_id + '(' + CAST(n.trade_amount AS VARCHAR) + ')', ', ') AS grouped_trades,
    
    -- Total Trade Amount
    SUM(n.trade_amount) AS total_trade_amount,

    -- Count of Trades
    COUNT(n.trade_id) AS trade_count

FROM redemption_position r
LEFT JOIN RankedTrades n 
    ON r.transaction_id = n.redemption_id AND n.rn = 1  -- Keep only trades assigned to the earliest redemption
GROUP BY 
    r.account_number, 
    r.transaction_id, 
    r.security_id, 
    r.amount, 
    r.redemption_date
ORDER BY r.account_number, r.redemption_date;
