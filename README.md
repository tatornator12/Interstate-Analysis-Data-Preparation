# Interstate Analysis Data Preparation

Geoprocessing Tool created to prepare nation-wide interstate HPMS (<a href="https://www.fhwa.dot.gov/policyinformation/hpms.cfm">Highway Performance Monitoring System</a>) and FARS data for further analysis:

* Take inputs for HPMS and FARS feature classes
* Extract out features associated with interstates,
* Create a point feature class representation for each state from the HPMS input
* Associate the closest FARS crash to the road point
* Calculate three crash rates using the crash counts and AADT (Annual Average Daily Traffic) values. The tool also requires an output workspace where each state road point dataset will be written to using the state code extracted from the HPMS input.
