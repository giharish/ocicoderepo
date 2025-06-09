CREATE TABLE loan_accounts (
    loan_id         VARCHAR2(20),
    customer_id     VARCHAR2(20),
    product_type    VARCHAR2(30),
    start_date      DATE,
    end_date        DATE,
    status          VARCHAR2(20)
);

CREATE TABLE repayment_schedule (
    loan_id         VARCHAR2(20),
    due_date        DATE,
    amount_due      NUMBER(10, 2),
    amount_paid     NUMBER(10, 2),
    payment_date    DATE
);

CREATE TABLE collections (
    agent_id         VARCHAR2(20),
    customer_id      VARCHAR2(20),
    visit_date       DATE,
    amount_collected NUMBER(10, 2),
    remarks          VARCHAR2(50)
);

CREATE TABLE disbursal_data (
    branch            VARCHAR2(50),
    loan_type         VARCHAR2(30),
    disbursal_date    DATE,
    disbursal_amount  NUMBER(12, 2)
);

CREATE TABLE interest_rates (
    loan_type     VARCHAR2(30),
    rate          NUMBER(5, 2),
    revised_date  DATE
);

CREATE TABLE delinquency_metrics (
    loan_id     VARCHAR2(20),
    dpd         NUMBER(5),
    bucket      VARCHAR2(10),
    npa_flag    CHAR(1)
);

CREATE INDEX idx_loan_accounts_loan_id ON loan_accounts(loan_id);
CREATE INDEX idx_loan_accounts_customer_id ON loan_accounts(customer_id);
CREATE INDEX idx_repayment_schedule_loan_id ON repayment_schedule(loan_id);
CREATE INDEX idx_collections_customer_id ON collections(customer_id);
CREATE INDEX idx_delinquency_metrics_loan_id ON delinquency_metrics(loan_id);
CREATE INDEX idx_disbursal_data_branch ON disbursal_data(branch);
CREATE INDEX idx_collections_agent_id ON collections(agent_id);
CREATE INDEX idx_delinquency_metrics_npa_flag ON delinquency_metrics(npa_flag);

ALTER TABLE loan_accounts ADD CONSTRAINT pk_loan_id PRIMARY KEY (loan_id);
ALTER TABLE loan_accounts ADD CONSTRAINT uq_customer_id UNIQUE (customer_id);

ALTER TABLE repayment_schedule
ADD CONSTRAINT fk_repay_loan
FOREIGN KEY (loan_id)
REFERENCES loan_accounts (loan_id)
ENABLE NOVALIDATE;

ALTER TABLE collections
ADD CONSTRAINT fk_coll_cust
FOREIGN KEY (customer_id)
REFERENCES loan_accounts (customer_id)
ENABLE NOVALIDATE;

ALTER TABLE delinquency_metrics
ADD CONSTRAINT fk_delinquency_loan
FOREIGN KEY (loan_id)
REFERENCES loan_accounts (loan_id)
ENABLE NOVALIDATE;

SELECT a.table_name, a.constraint_name, a.status, a.validated
FROM user_constraints a
WHERE a.constraint_type = 'R';

CREATE MATERIALIZED VIEW mv_delinquency_metrics
REFRESH COMPLETE
START WITH SYSDATE
NEXT SYSDATE + 1  -- Refresh daily
AS
SELECT
    r.loan_id,
    CASE
        WHEN r.amount_paid < r.amount_due THEN TRUNC(SYSDATE) - r.due_date
        ELSE 0
    END AS dpd,
    CASE
        WHEN r.amount_paid < r.amount_due AND TRUNC(SYSDATE) - r.due_date BETWEEN 1 AND 30 THEN '30+'
        WHEN r.amount_paid < r.amount_due AND TRUNC(SYSDATE) - r.due_date BETWEEN 31 AND 60 THEN '60+'
        WHEN r.amount_paid < r.amount_due AND TRUNC(SYSDATE) - r.due_date BETWEEN 61 AND 90 THEN '90+'
        WHEN r.amount_paid < r.amount_due AND TRUNC(SYSDATE) - r.due_date > 90 THEN '180+'
        ELSE 'Current'
    END AS bucket,
    CASE
        WHEN r.amount_paid < r.amount_due AND TRUNC(SYSDATE) - r.due_date > 90 THEN 'Y'
        ELSE 'N'
    END AS npa_flag
FROM repayment_schedule r
JOIN (
    SELECT loan_id, MAX(due_date) AS last_due
    FROM repayment_schedule
    GROUP BY loan_id
) last_due_info
ON r.loan_id = last_due_info.loan_id AND r.due_date = last_due_info.last_due;

