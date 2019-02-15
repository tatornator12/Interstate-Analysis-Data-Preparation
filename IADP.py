# Import Modules
import os
import arcpy
import sys
import traceback


# Creates a unique list of values for a specific field
def uniqueList(layer, field):
    with arcpy.da.SearchCursor(layer, [field]) as cursor:
        new_set = sorted({row[0] for row in cursor})

    new_list = [int(x) for x in new_set]

    return new_list


# Filters input HPMS feature class for Interstates
def hpmsFilter(hpms_fc):
    arcpy.AddMessage("Filtering out " + hpms_fc + " for interstates...")

    try:
        arcpy.env.workspace = out_workspace
        HPMS_fields = arcpy.ListFields(hpms_fc)
        for field in HPMS_fields:
            if 'f_system' in field.name.lower():
                hpmsFSystemExp = field.name + " = 1"
                arcpy.MakeFeatureLayer_management(hpms_fc, 'HPMS_F_System_lyr')
                arcpy.SelectLayerByAttribute_management('HPMS_F_System_lyr', "NEW_SELECTION", hpmsFSystemExp)
                arcpy.CopyFeatures_management('HPMS_F_System_lyr', memDB + "\HPMS_F_System_1")
                hpms_result = arcpy.Project_management(memDB + '\HPMS_F_System_1', 'HPMS_F_System_1_prj', out_coordinate_system)
                return hpms_result

    except arcpy.ExecuteError:
        msgs = arcpy.GetMessages(2)
        arcpy.AddError(msgs)
        print(msgs)
        print("Check to make sure that the field name 'f_system' is in the data.")


# Filters input FARS feature class for Interstate Crashes
def farsFilter(fars_fc):
    arcpy.AddMessage("Filtering out " + fars_fc + " for crashes that fall along an interstate...")

    try:
        arcpy.env.workspace = out_workspace
        FARS_fields = arcpy.ListFields(fars_fc)
        FARS_fields = [field.name.lower() for field in FARS_fields]
        neededFARSfields = ['x_y_valid', 'a_inter']
        if all(field in FARS_fields for field in neededFARSfields):
            farsPrepExp = 'x_y_valid = 1 AND a_inter = 1'
            arcpy.MakeFeatureLayer_management(fars_fc, 'FARS_Filtered_lyr')
            arcpy.SelectLayerByAttribute_management('FARS_Filtered_lyr', "NEW_SELECTION", farsPrepExp)
            arcpy.CopyFeatures_management('FARS_Filtered_lyr', memDB + "\FARS_Filtered")
            fars_result = arcpy.Project_management(memDB + '\FARS_Filtered', 'FARS_Filtered_prj', out_coordinate_system)
            return fars_result

    except arcpy.ExecuteError:
        msgs = arcpy.GetMessages(2)
        arcpy.AddError(msgs)
        print(msgs)
        print("Check to make sure that the field names 'x_y_valid' and 'a_inter' are in the data.")


# Creates a road point feature class representation with crash counts and crash rates for each state
def dataPrep(merge_fc, hpms_fc, near_dist, linear_unit):

    try:

        # Create a Unique List of States
        state_list = uniqueList(out_workspace + "\HPMS_F_System_1_prj", "state_code")

        # Loop Through Each State in List
        for state in state_list:

            arcpy.AddMessage("Processing road and crash data where state code = {}...".format(state))

            # Prepare Expressions for Selection
            hpmsStateExp = "state_code = {}".format(state)
            farsStateExp = "state = {}".format(state)

            # Create Feature Layers
            arcpy.MakeFeatureLayer_management(out_workspace + "\HPMS_F_System_1_prj", 'HPMS_state_lyr')
            arcpy.MakeFeatureLayer_management(out_workspace + "\FARS_Filtered_prj", 'FARS_Filtered_state_lyr')

            # Select Features by State
            arcpy.SelectLayerByAttribute_management('HPMS_state_lyr', "NEW_SELECTION", hpmsStateExp)
            arcpy.SelectLayerByAttribute_management('FARS_Filtered_state_lyr', "NEW_SELECTION", farsStateExp)

            # Copy the Selected Features to New Layers
            arcpy.CopyFeatures_management('HPMS_state_lyr', memDB + "\HPMS_{}".format(state))
            arcpy.CopyFeatures_management('FARS_Filtered_state_lyr', memDB + "\FARS_Filtered_{}".format(state))

            # Create a Unique List of Route Numbers by State
            int_list = uniqueList(memDB + "\HPMS_{}".format(state), "route_numb")

            # Loop Through Each Route in List
            for interstate in int_list:
                # Prepare Expressions for Selection
                hpmsInterstateExp = "route_numb = {}".format(interstate)
                farsInterstateExp = "tway_id LIKE '%I-{}%'".format(interstate)

                # Create Feature Layers
                arcpy.MakeFeatureLayer_management(memDB + "\HPMS_{}".format(state), "HPMS_{}_lyr".format(state))
                arcpy.MakeFeatureLayer_management(memDB + '\FARS_Filtered_{}'.format(state),
                                                  'FARS_Filtered_{}_lyr'.format(state))

                # Setup Field Mappings
                fieldmappings = arcpy.FieldMappings()
                fieldmappings.addTable('HPMS_{}_lyr'.format(state))

                # Select Features by Route
                arcpy.SelectLayerByAttribute_management('HPMS_{}_lyr'.format(state), 'NEW SELECTION', hpmsInterstateExp)
                arcpy.SelectLayerByAttribute_management('FARS_Filtered_{}_lyr'.format(state), 'NEW SELECTION',
                                                        farsInterstateExp)

                # Copy Selected Features to New Layers
                arcpy.CopyFeatures_management("HPMS_{}_lyr".format(state),
                                              memDB + "\HPMS_{0}_{1}".format(state, interstate))
                arcpy.CopyFeatures_management('FARS_Filtered_{}_lyr'.format(state),
                                              memDB + '\FARS_Filtered_{0}_{1}'.format(state, interstate))

                # Dissolve Road Network to Single Feature
                arcpy.management.Dissolve(memDB + "\HPMS_{0}_{1}".format(state, interstate),
                                          memDB + "\HPMS_{0}_Dis_{1}".format(state, interstate),
                                          "route_numb", None, "MULTI_PART", "DISSOLVE_LINES")

                # Generate Points Along Road Network at Consistent Lengths
                arcpy.management.GeneratePointsAlongLines(memDB + "\HPMS_{0}_Dis_{1}".format(state, interstate),
                                                          memDB + "\HPMS_{0}_{1}_pts".format(state, interstate), "DISTANCE",
                                                          "0.1 Miles", None, None)

                # Spatially Join Road Network Attribution to Point Dataset
                arcpy.analysis.SpatialJoin(memDB + "\HPMS_{0}_{1}_pts".format(state, interstate),
                                           "HPMS_{}_lyr".format(state),
                                           memDB + "\HPMS_pts_sj_{0}_{1}".format(state, interstate), "JOIN_ONE_TO_ONE",
                                           "KEEP_ALL",
                                           fieldmappings, "INTERSECT")

                # Add Crash Count Field to Road Point Dataset
                arcpy.AddField_management(memDB + "\HPMS_pts_sj_{0}_{1}".format(state, interstate), 'Crash_Count', 'SHORT',
                                          '', '', '', 'Crash Count')

                # Run Near Analysis on Crash Dataset to Generate a Distance to Nearest Road Point
                arcpy.Near_analysis(memDB + '\FARS_Filtered_{0}_{1}'.format(state, interstate),
                                    memDB + "\HPMS_pts_sj_{0}_{1}".format(state, interstate),
                                    None, 'NO_LOCATION', "NO_ANGLE", "PLANAR")

                # Determine Selected Linear Unit
                fars_sr = arcpy.Describe(memDB + '\FARS_Filtered_{0}_{1}'.format(state, interstate)).SpatialReference
                fc_linear_unit = fars_sr.linearUnitName + 's'
                if linear_unit != fc_linear_unit:
                    if linear_unit == 'Kilometers':
                        km_exp = '!NEAR_DIST! * 0.001'
                        arcpy.CalculateField_management(memDB + '\FARS_Filtered_{0}_{1}'.format(state, interstate),
                                                         'NEAR_DIST', km_exp, 'PYTHON3', None)
                    elif linear_unit == 'Miles':
                        m_exp = '!NEAR_DIST! * 0.00062137'
                        arcpy.CalculateField_management(memDB + '\FARS_Filtered_{0}_{1}'.format(state, interstate),
                                                         'NEAR_DIST', m_exp, 'PYTHON3', None)
                    elif linear_unit == 'Feet':
                        f_exp = '!NEAR_DIST! * 3.2808'
                        arcpy.CalculateField_management(memDB + '\FARS_Filtered_{0}_{1}'.format(state, interstate),
                                                        'NEAR_DIST', f_exp, 'PYTHON3', None)

                arcpy.CopyFeatures_management(memDB + '\FARS_Filtered_{0}_{1}'.format(state, interstate), out_workspace + '\FARS_Filtered_{0}_{1}'.format(state, interstate))

                # Select All Crashes within Specified Distance
                arcpy.MakeFeatureLayer_management(memDB + '\FARS_Filtered_{0}_{1}'.format(state, interstate),
                                                  'FARS_Filtered_{0}_{1}_lyr'.format(state, interstate))
                crashDistExp = "NEAR_DIST < {}".format(near_dist)
                arcpy.SelectLayerByAttribute_management('FARS_Filtered_{0}_{1}_lyr'.format(state, interstate),
                                                        'NEW_SELECTION', crashDistExp)

                # Run Frequency Analysis to get Crash Total for each Road Point
                arcpy.Frequency_analysis('FARS_Filtered_{0}_{1}_lyr'.format(state, interstate),
                                         memDB + '\FARS_Filtered_{0}_{1}_freq'.format(state, interstate), 'NEAR_FID', None)

                # Join Crash Totals to Road Point Dataset
                arcpy.MakeFeatureLayer_management(memDB + "\HPMS_pts_sj_{0}_{1}".format(state, interstate),
                                                  'HPMS_pts_sj_{0}_{1}_lyr'.format(state, interstate))
                arcpy.AddJoin_management('HPMS_pts_sj_{0}_{1}_lyr'.format(state, interstate), 'OID',
                                         memDB + '\FARS_Filtered_{0}_{1}_freq'.format(state, interstate),
                                         'NEAR_FID', 'KEEP_ALL')
                farsFrequencyExp = '!FARS_Filtered_{0}_{1}_freq.FREQUENCY!'.format(state, interstate)
                arcpy.CalculateField_management('HPMS_pts_sj_{0}_{1}_lyr'.format(state, interstate), 'Crash_Count',
                                                farsFrequencyExp, 'PYTHON3', None)
                arcpy.RemoveJoin_management('HPMS_pts_sj_{0}_{1}_lyr'.format(state, interstate))

            # Merge All Interstate Point Datasets
            arcpy.env.workspace = memDB
            mem_fcList = arcpy.ListFeatureClasses('HPMS_pts_sj_{0}_*'.format(state))
            arcpy.Merge_management(mem_fcList, merge_fc + "_{}".format(state))

            # Add Crash_Rate Fields to Merged Dataset
            arcpy.AddFields_management(merge_fc + "_{}".format(state),
                                       [['Crash_Rate_A', 'DOUBLE', 'Crash Rate A'],
                                        ['Crash_Rate_B', 'DOUBLE', 'Crash Rate B'],
                                        ['Crash_Rate_C', 'DOUBLE', 'Crash Rate C']])

            # Calculate Each Crash_Rate
            crashRateAExp = "(!Crash_Count! * 100000000) / (!AADT_VN! * 365 * 1 * .10)"
            crashRateBExp = "!Crash_Count! / (!AADT_VN! * .10)"
            crashRateCExp = "!Crash_Count! / (!AADT_VN! / .10)"
            arcpy.CalculateFields_management(merge_fc + "_{}".format(state), 'PYTHON3',
                                             [['Crash_Rate_A', crashRateAExp], ['Crash_Rate_B', crashRateBExp],
                                              ['Crash_Rate_C', crashRateCExp]])

            # Delete Any Fields Leftover from Previous Analyses
            arcpy.DeleteField_management(merge_fc + "_{}".format(state), ['Join_Count', 'TARGET_FID'])

            # Clear In Memory Database
            arcpy.Delete_management("in_memory")

            arcpy.AddMessage(hpms_fc + "_{}".format(state) + " has completed.")
            arcpy.AddMessage("-------------------------------")

        # Clear the Output Workspace
        arcpy.env.workspace = out_workspace
        arcpy.Delete_management("HPMS_F_System_1_prj")
        arcpy.Delete_management("FARS_Filtered_prj")

    except arcpy.ExecuteError:
        msgs = arcpy.GetMessages(2)
        arcpy.AddError(msgs)
        print(msgs)
    except:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
        msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"
        arcpy.AddError(pymsg)
        arcpy.AddError(msgs)
        print(pymsg)
        print(msgs)


if __name__ == "__main__":

    # Define Inputs
    HPMS_featureclass = arcpy.GetParameterAsText(0)
    FARS_featureclass = arcpy.GetParameterAsText(1)
    crash_distance = arcpy.GetParameterAsText(2)
    in_linear_unit = arcpy.GetParameterAsText(3)
    out_workspace = arcpy.GetParameterAsText(4)
    merge_featureclass = os.path.join(out_workspace, os.path.basename(HPMS_featureclass))
    memDB = str('in_memory')
    out_coordinate_system = arcpy.SpatialReference('USA Contiguous Equidistant Conic')
    arcpy.env.overwriteOutput = True

    # Execute Functions
    hpmsFilter(HPMS_featureclass)
    farsFilter(FARS_featureclass)
    dataPrep(merge_featureclass, HPMS_featureclass, crash_distance, in_linear_unit)
