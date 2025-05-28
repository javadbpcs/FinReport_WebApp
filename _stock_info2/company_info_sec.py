SEC_API='4e91065eb767b593770ecbd9ad49d01b11d59525cc33f9c54e8d8666f5ba41e9'

from sec_api import ExtractorApi

extractorApi = ExtractorApi(SEC_API)

filing_url = "https://www.sec.gov/Archives/edgar/data/1318605/000156459021004599/tsla-10k_20201231.htm"

section_text = extractorApi.get_section(filing_url, "1", "text")

print(section_text)


