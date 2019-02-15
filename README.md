# Interstate Analysis Data Preparation

Geoprocessing Tool Purpose: (1) Take inputs for HPMS and FARS feature classes, (2) extract out features associated with interstates, (3) create a point feature class representation for each state from the HPMS input, (4) associate the closest FARS crash to the road point, and (5) calculate three crash rates using the crash counts and AADT (Annual Average Daily Traffic) values. The tool also requires an output workspace where each state road point dataset will be written to using the state code extracted from the HPMS input.
