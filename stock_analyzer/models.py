from django.db import models
from dashboard.models import Report

# Create your models here.

class StockAnalysis(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='stock_analyses')
    stock_symbol = models.CharField(max_length=10)
    analysis_result = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.stock_symbol} Analysis for {self.report.name}"

    class Meta:
        verbose_name_plural = "Stock Analyses"
        ordering = ['-created_at']

class CompanyProfile(models.Model):
    stock_symbol = models.CharField(max_length=10, unique=True)
    company_name = models.CharField(max_length=255)
    sector = models.CharField(max_length=100, null=True, blank=True)
    industry = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    logo_url = models.URLField(null=True, blank=True)
    employee_count = models.IntegerField(null=True, blank=True)
    market_cap = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company_name} ({self.stock_symbol})"

    class Meta:
        ordering = ['stock_symbol']

class FinancialStatement(models.Model):
    STATEMENT_TYPES = (
        ('income', 'Income Statement'),
        ('balance', 'Balance Sheet'),
        ('cash_flow', 'Cash Flow Statement'),
    )
    
    PERIOD_TYPES = (
        ('annual', 'Annual'),
        ('quarterly', 'Quarterly'),
    )
    
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='financial_statements')
    statement_type = models.CharField(max_length=20, choices=STATEMENT_TYPES)
    period_type = models.CharField(max_length=20, choices=PERIOD_TYPES)
    fiscal_year = models.IntegerField()
    fiscal_period = models.CharField(max_length=10)
    filing_date = models.DateField()
    data = models.JSONField()
    source = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.stock_symbol} - {self.get_statement_type_display()} - {self.fiscal_year} {self.fiscal_period}"

    class Meta:
        ordering = ['-filing_date']

class ValuationMetric(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='valuation_metrics')
    date = models.DateField()
    pe_ratio = models.FloatField(null=True, blank=True)
    pb_ratio = models.FloatField(null=True, blank=True)
    ps_ratio = models.FloatField(null=True, blank=True)
    peg_ratio = models.FloatField(null=True, blank=True)
    ev_to_ebitda = models.FloatField(null=True, blank=True)
    dividend_yield = models.FloatField(null=True, blank=True)
    profit_margin = models.FloatField(null=True, blank=True)
    roe = models.FloatField(null=True, blank=True)
    roa = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.stock_symbol} Valuation - {self.date}"

    class Meta:
        ordering = ['-date']

class TechnicalIndicator(models.Model):
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='technical_indicators')
    date = models.DateField()
    sma_20 = models.FloatField(null=True, blank=True)
    sma_50 = models.FloatField(null=True, blank=True)
    sma_200 = models.FloatField(null=True, blank=True)
    ema_12 = models.FloatField(null=True, blank=True)
    ema_26 = models.FloatField(null=True, blank=True)
    rsi_14 = models.FloatField(null=True, blank=True)
    macd = models.FloatField(null=True, blank=True)
    macd_signal = models.FloatField(null=True, blank=True)
    macd_histogram = models.FloatField(null=True, blank=True)
    bollinger_upper = models.FloatField(null=True, blank=True)
    bollinger_middle = models.FloatField(null=True, blank=True)
    bollinger_lower = models.FloatField(null=True, blank=True)
    volume = models.BigIntegerField(null=True, blank=True)
    beta = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.stock_symbol} Technical - {self.date}"

    class Meta:
        ordering = ['-date']

class InvestmentScore(models.Model):
    RECOMMENDATION_CHOICES = (
        ('strong_buy', 'Strong Buy'),
        ('buy', 'Buy'),
        ('hold', 'Hold'),
        ('sell', 'Sell'),
        ('strong_sell', 'Strong Sell'),
    )
    
    company = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE, related_name='investment_scores')
    date = models.DateField()
    valuation_score = models.FloatField()
    growth_score = models.FloatField()
    profitability_score = models.FloatField()
    financial_health_score = models.FloatField()
    technical_score = models.FloatField()
    sentiment_score = models.FloatField()
    overall_score = models.FloatField()
    recommendation = models.CharField(max_length=20, choices=RECOMMENDATION_CHOICES)
    analysis_summary = models.TextField()
    key_strengths = models.TextField(null=True, blank=True)
    key_risks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.stock_symbol} Score - {self.date}"
        
    def format_recommendation(self):
        """Return the recommendation with underscores replaced by spaces and uppercase"""
        return self.recommendation.replace('_', ' ').upper()

    class Meta:
        ordering = ['-date']

class EconomicIndicator(models.Model):
    """
    Stores economic indicator data retrieved from FRED API
    """
    INDICATOR_TYPES = (
        ('interest_rate', 'Federal Funds Rate'),
        ('unemployment', 'Unemployment Rate'),
        ('inflation', 'Consumer Price Index'),
        ('gdp', 'GDP Growth Rate'),
        ('yield_curve', '10Y-2Y Treasury Spread'),
    )
    
    indicator_type = models.CharField(max_length=50, choices=INDICATOR_TYPES)
    date = models.DateField()
    value = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_indicator_type_display()} - {self.date}"
    
    class Meta:
        ordering = ['-date']
        unique_together = ['indicator_type', 'date']
