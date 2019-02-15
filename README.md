# Interstate Analysis Data Preparation

Geoprocessing tool created as part of a project to prepare nation-wide interstate HPMS (<a href="https://www.fhwa.dot.gov/policyinformation/hpms.cfm">Highway Performance Monitoring System</a>) and FARS (<a href="https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars">Fatality Analysis Reporting System</a>) data on a yearly basis for further analysis.

### The steps of the tool are as follows:

1. Take inputs for HPMS and FARS feature classes
2. Extract out features associated with interstates
3. Create a point feature class representation for each state from the HPMS input
4. Associate the closest FARS crash to the road point
5. Calculate three crash rates using the crash counts and AADT (Annual Average Daily Traffic) values. The tool also requires an output workspace where each state road point dataset will be written to using the state code extracted from the HPMS input.
