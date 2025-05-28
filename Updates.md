## [0.4.2] - 2025-05-08
#### MJ Highlights:
- replaced yahoo finance with Polygon and updates to UI (since Yahoo fincane was giving rate limits)
## [0.5.0] - 2025-05-09
#### MJ Highlights:
- addition of "stock dashboard" and "stock search" capabilities and buttons to report page
- addition of "economic indicators" page and capability to top of the side bar
- saving data from "economic indicators" and addition of refresh button if you need an updated data
- fix of sidebar rendering problem in the newly created pages
- addition of SEC-API and FRED APIs beside the Polygon.io (detailed info at the bottom)
#### Added
- Comprehensive data model with classes for CompanyProfile, FinancialStatement, ValuationMetric, TechnicalIndicator, AnalystRecommendation, InsiderTransaction, EconomicIndicator, NewsArticle, and InvestmentScore
- Integration services for *Polygon.io, SEC-API, and FRED APIs*
- Functions for fetching company information, price data, financial ratios, technical indicators, and economic data
- Investment potential scoring algorithm
- API endpoints for retrieving price data for interactive charts
- Front-end templates for stock dashboard, economic dashboard, and search interfaces
#### Changed
- Enhanced view functions for comprehensive stock dashboard
- Updated search functionality with improved UX
- Modified economic indicators view for better data visualization
- economic indicators
#### Fixed
- Adjusted styling for consistent UI appearance
- Improved chart responsiveness across devices
#### Known Issues
- Environment configuration problems with Django migrations

## APIs Used for Data Collection - 2025-05-09
### Stock Dashboard
- **Polygon.io** - Company information, stock prices, technical indicators
- **SEC-API** - Financial statements, earnings reports, insider transactions
- **FRED** (Federal Reserve Economic Data) - Economic context data

### Stock Search
- **Polygon.io** - Company lookups, stock symbol validation, basic metrics
- **SEC-API** - Company filing information

### Economic Indicators
- **FRED** (Federal Reserve Economic Data) - Primary source for:
  - Interest rates
  - Inflation data (CPI)
  - Unemployment figures
  - Yield curve data
  - GDP growth
  - Other macroeconomic indicators

> Note: Yahoo Finance was previously used but was replaced with Polygon.io due to rate limit issues.


