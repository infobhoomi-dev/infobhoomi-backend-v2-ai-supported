from django.urls import path, include
from .views import  *
from rest_framework.routers import DefaultRouter


urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('create/', CreateUserView.as_view(), name='create_user'),

    path('login/', LoginView.as_view(), name='login'),
    path('me/', UserDetailView.as_view(), name='me'),
    path('list/', GetUserAccountsView.as_view(), name='users_list'), # get user list for Admin Panal
    path('list-add-user-roles/', GetUserAccounts_Add_UserRoles_View.as_view(), name='users_list'),
    
    path('logout/', LogoutView.as_view(), name='logout'),

    path('change_password/', ChangePasswordView.as_view(), name='change_password'),
    path('reset_password/', ResetPasswordView.as_view(), name='reset_password'),
    path('update/user_id=<int:pk>/', UpdateUserView.as_view()), # update user details for admin

    path('check-password/', PasswordCheckAPIView.as_view(), name='check-password'),
    path('verify-token/', VerifyTokenView.as_view(), name='check-token'),
    path('user-authentication/', Verify_User_Auth_Login_View.as_view()),

    path('recent_logins/', Recent_Users_Login_View.as_view()),
    path('user_overview/', User_Over_View.as_view()),
    path('user-online/', UserAccounts_online_View.as_view()),

    path('admin_acc_data/', Admin_Acc_Data_View.as_view(), name='admin-accounts'), # Data for "contact admin"

#_________________________________________________________ List APIs ______________________________________________________________________

    path('lst-sl-party-type-1/', Lst_SL_Party_Type_1_View.as_view()), #__ Lst_SL_Party_Type_1 __
    path('lst-sl-partyroletype-2/', Lst_SL_PartyRoleType_2_View.as_view()), #__ Lst_SL_PartyRoleType_2 __
    path('lst-sl-education-level-3/', Lst_SL_Education_Level_3_View.as_view()), #__ Lst_SL_Education_Level_3 __
    path('lst-sl-race-4/', Lst_SL_Race_4_View.as_view()), #__ Lst_SL_Race_4 __
    path('lst-sl-health-status-5/', Lst_SL_HealthStatus_5_View.as_view()), #__ Lst_SL_HealthStatus_5 __
    path('lst-sl-married-status-6/', Lst_SL_MarriedStatus_6_View.as_view()), #__ Lst_SL_MarriedStatus_6 __
    path('lst-sl-religions-7/', Lst_SL_Religions_7_View.as_view()), #__ Lst_SL_Religions_7 __
    path('lst-sl-gendertype-8/', Lst_SL_GenderType_8_View.as_view()), #__ Lst_SL_GenderType_8 __
    path('lst-sl-righttype-9/', Lst_SL_RightType_9_View.as_view()), #__ Lst_SL_RightType_9 __
    path('lst-sl-baunittype-10/', Lst_SL_BAUnitType_10_View.as_view()), #__ Lst_SL_BAUnitType_10 __
    path('lst-sl-adminrestrictiontype-11/', Lst_SL_AdminRestrictionType_11_View.as_view()), #__ Lst_SL_AdminRestrictionType_11 __
    path('lst-sl-annotationtype-12/', Lst_SL_AnnotationType_12_View.as_view()), #__ Lst_SL_AnnotationType_12 __
    path('lst-sl-mortgagetype-13/', Lst_Sl_MortgageType_13_View.as_view()), #__ Lst_Sl_MortgageType_13 __
    path('lst-sl-rightsharetype-14/', Lst_SL_RightShareType_14_View.as_view()), #__ Lst_SL_RightShareType_14 __
    path('lst-sl-administrativestataustype-15/', Lst_SL_AdministrativeStatausType_15_View.as_view()), #__ Lst_SL_AdministrativeStatausType_15 __
    path('lst-sl-administrativesourcetype-16/', Lst_SL_AdministrativeSourceType_16_View.as_view()), #__ Lst_SL_AdministrativeSourceType_16 __
    path('lst-sl-responsibilitytype-17/', Lst_SL_ResponsibilityType_17_View.as_view()), #__ Lst_SL_ResponsibilityType_17 __
    path('lst-la-baunittype-18/', Lst_LA_BAUnitType_18_View.as_view()), #__ Lst_LA_BAUnitType_18 __
    path('lst-su-sl-levelcontenttype-19/', Lst_SU_SL_LevelContentType_19_View.as_view()), #__ Lst_SU_SL_LevelContentType_19 __
    path('lst-su-sl-regestertype-20/', Lst_SU_SL_RegesterType_20_View.as_view()), #__ Lst_SU_SL_RegesterType_20 __
    path('lst-su-sl-structuretype-21/', Lst_SU_SL_StructureType_21_View.as_view()), #__ Lst_SU_SL_StructureType_21 __
    path('lst-su-sl-water-22/', Lst_SU_SL_Water_22_View.as_view()), #__ Lst_SU_SL_Water_22 __
    path('lst-su-sl-sanitation-23/', Lst_SU_SL_Sanitation_23_View.as_view()), #__ Lst_SU_SL_Sanitation_23 __
    path('lst-su-sl-roof-type-24/', Lst_SU_SL_Roof_Type_24_View.as_view()), #__ Lst_SU_SL_Roof_Type_24 __
    path('lst-su-sl-wall-type-25/', Lst_SU_SL_Wall_Type_25_View.as_view()), #__ Lst_SU_SL_Wall_Type_25 __
    path('lst-su-sl-floor-type-26/', Lst_SU_SL_Floor_Type_26_View.as_view()), #__ Lst_SU_SL_Floor_Type_26 __
    path('lst-sr-sl-spatialsourcetypes-27/', Lst_SR_SL_SpatialSourceTypes_27_View.as_view()), #__ Lst_SR_SL_SpatialSourceTypes_27 __
    path('lst-ec-extlandusetype-28/', Lst_EC_ExtLandUseType_28_View.as_view()), #__ Lst_EC_ExtLandUseType_28 __
    path('lst-ec-extlandusesubtype-29/', Lst_EC_ExtLandUseSubType_29_View.as_view()), #__ Lst_EC_ExtLandUseSubType_29 __
    path('lst-ec-extouterlegalspaceusetype-30/', Lst_EC_ExtOuterLegalSpaceUseType_30_View.as_view()), #__ Lst_EC_ExtOuterLegalSpaceUseType_30 __
    path('lst-ec-extouterlegalspaceusesubtype-31/', Lst_EC_ExtOuterLegalSpaceUseSubType_31_View.as_view()), #__ Lst_EC_ExtOuterLegalSpaceUseSubType_31 __
    path('lst-ec-extbuildusetype-32/', Lst_EC_ExtBuildUseType_32_View.as_view()), #__ Lst_EC_ExtBuildUseType_32 __
    path('lst-ec-extbuildusesubtype-33/', Lst_EC_ExtBuildUseSubType_33_View.as_view()), #__ Lst_EC_ExtBuildUseSubType_33 __
    path('lst-ec-extdivisiontype-34/', Lst_EC_ExtDivisionType_34_View.as_view()), #__ Lst_EC_ExtDivisionType_34 __
    path('lst-ec-extfeaturemaintype-35/', Lst_EC_ExtFeatureMainType_35_View.as_view()), #__ Lst_EC_ExtFeatureMainType_35 __
    path('lst-ec-extfeatureytype-36/', Lst_EC_ExtFeatureMainType_36_View.as_view()), #__ Lst_EC_ExtFeatureMainType_36 __
    path('lst-ec-extfeaturebuildtype-37/', Lst_EC_ExtFeatureMainType_37_View.as_view()), #__ Lst_EC_ExtFeatureMainType_37 __
    path('lst-tele-providers-38/', Lst_Tele_Providers_38_View.as_view()), #__ Lst_Telecom_Providers_38 __
    path('lst-int-providers-39/', Lst_Int_Providers_39_View.as_view()), #__ Lst_Internet_Providers_39 __
    path('lst-org-name-40/', Lst_Org_Names_40_View.as_view()), #__ Lst_Organization_Names_40 __
    path('lst-sl-group_party_type-41/', Lst_SL_Group_Party_Type_41_View.as_view()), #__ Lst_SL_Group_Party_Type_41 __
    path('lst-gnd-area/', Lst_gnd_10m_View.as_view()), #__ Lst_gnd_for Admin Info __

#__________________________________________________________________________________________________________________________________________


#__ Test __
    path('test-json/', TestJsonView.as_view(), name='spatial data post'),
    path('test-data/', Test_Data_MyLayerIDs_View.as_view(), name='test data post'),
    path('temp_import/', Temp_Import_View.as_view()),

#__ CityJson __
    path('cityjson/', CityJSON_Model_ListCreate.as_view(), name='cityjson-list-create'),
    path('cityjson/<int:pk>/', CityJSON_Model_Retrieve.as_view(), name='cityjson-retrieve'),
    path('cityjson/upload/', CityJSON_Upload.as_view(), name='cityjson-upload'),

    path('cityobjects/', City_Object_List.as_view(), name='cityobject-list'),
    path('cityobjects/<str:pk>/', City_Object_Retrieve.as_view(), name='cityobject-retrieve'),


    # path('ifc_to_cityjson/', IFCtoCityJSONView.as_view(), name='ifc_to_cityjson'),


#__________________________________________________________________________________________________________________________________________


#__ sl_gnd_10m __
    path('gnd_all/', GND_All_View.as_view()),

    path('pd-list/', PD_List_View.as_view()),
    path('pd-data/<str:pd_name>/', PD_Data_View.as_view()), # Get GND DATA for set org area by super.admin

    path('dist-list/', Dist_List_View.as_view()),


#__ Organization Area __
    path('org-area-get/org_id=<int:org_id>/', Org_Area_By_OrgID_View.as_view()), # Get org area by org_id for super.admin panel
    path('org-area/update/org_id=<int:org_id>/', Org_Area_Update_View.as_view()),

    path('org_area/', GND_By_Org_Area_View.as_view()), # Get the org area for user at login


#__ Organization Location __
    path('org_loc/org_id=<int:org_id>/', Org_Location_Get_by_ID_View.as_view()), # Get org location by org_id for super.admin panel
    path('org_loc/update/org_id=<int:org_id>/', Org_Location_Update_View.as_view()),

    path('org_loc_get/', Org_Location_Get_View.as_view()), # Get map initializing point for user login 


#__ SL_Organization __
    path('sl-orgnization/', SL_Organization_View.as_view()), # Create orginization (save) API & get org list for super.admin panel
    path('sl-orgnization/org_id=<int:pk>/', SL_Organization_Get_By_ID_View.as_view()), # Get org details for super.admin
    path('sl-organization/update/org_id=<int:pk>/', SL_Organization_Update_View.as_view()),

    path('org_details/', Org_Detail_View.as_view()), # Get organization details by user's org_id


#__ User Roles __
    path('user-roles/', User_Roles_Create_View.as_view()), # User Roles create
    path('user-roles/update/role_id=<int:pk>/', User_Role_update_View.as_view()), # User Roles update
    path('user-roles/delete/role_id=<int:pk>/', User_Role_delete_View.as_view()),

    path('user-roles-get-admin/', User_Role_View_filter_admin.as_view()), # Get User Role list for Admin Login

#__ Role Permission __
    path('role-permission/', Role_Permission_Filter_View.as_view()), # Get permission by role_id and permission_ids
    path('role-permission-all/role_id=<int:role_id>/', Role_Permission_All_View.as_view()), # Get permissions for Admin Panel
    path('role-permission-layerpanel/', Role_Permission_LayerPanel_View.as_view()), # Get permission for Layer Panel

    path('role-permission/update/id=<int:pk>/', Role_Permission_Update_View.as_view()),


#__ Layer DATA __
    path('layerdata/', LayerData_Create_View.as_view()), # Layer data post (Create)

    path('layerdata_get_user/', LayerData_Get_User_View.as_view()), # Get layer data for user login (Default, org. and user created)
    path('layerdata_get_admin/', LayerData_Get_Admin_View.as_view()), # Get layer data for admin login
    path('layerdata_get_admin_panel/', LayerData_Get_AdminControlPanel_View.as_view()), # Layer data for admin panel

    path('layerdata/update/id=<int:pk>/', Layer_Update_View.as_view()), # Layer update
    path('layerdata/delete/id=<int:pk>/', Layer_Delete_View.as_view()), # Layer delete

#__ Survey Rep DATA __
    path('survey_rep_data/', Survey_Rep_DATA_Save_View.as_view()), # Survey Rep data post
    path('survey_rep_data_user/', Survey_Rep_DATA_Filter_User_View.as_view()), # Get Survey Rep data filter by username 

    path('survey_rep_data/update/id=<int:pk>/', Survey_Rep_DATA_Update_View.as_view()), # Survey Rep data update by id
    path('survey_rep_data/bulk_delete/', Survey_Rep_DATA_BulkDelete_id_View.as_view()), # Survey Rep data bulk delete

#__ Survey Rep History __
    path('survey_rep_history/su_id=<int:su_id>/', Survey_Rep_History_View_filter.as_view()), # Survey Rep history get
    path('survey_rep_history/update/id=<int:pk>/', Survey_Rep_History_View_update.as_view()), # Survey Rep history update
    path('survey_rep_history_username/', Survey_Rep_History_View_filter_username.as_view()), # Survey Rep history get by username

#__ Geom Create By __
    path('create_by/', Geom_Create_by_View.as_view()), # Geom create by info for admin

#__ Search Geom __
    path('search/', Search_Geom_View.as_view()),
    path('query-parcels/', Query_Parcels_View.as_view()),
    path('query-parcels/export-shp/', Query_Parcels_SHP_Export_View.as_view()),

#__ Party __
    path('sl-party/', Party_View.as_view()),
    path('sl-party-data/', Party_Data_Get_View.as_view()),
    path('sl-party-data-pid/', Party_Data_Get_PID_View.as_view()),
    path('sl-party-data-type/<str:type>/', Party_Data_View_Type.as_view()),
    path('sl-party/update/pid=<int:pk>/', Party_Update_View.as_view()),

#__ SL_Department __
    path('sl-department/', SL_Department_View.as_view()),
    path('sl-department-list/', SL_Department_List_View.as_view()),

    path('sl-department/update/id=<int:pk>/', SL_Department_Update_Delete_View.as_view()), # both update and delete method in this API


#__ Land Summary Info __
    path('lnd-summary/su_id=<str:su_id>/', Lnd_Summary_View.as_view()),

#__ Land Admin Info __
    path('lnd-admin-info/su_id=<str:su_id>/', Lnd_Admin_Info_View.as_view()), # Get Administrative Information
    path('lnd-admin-info/update/su_id=<str:su_id>/', Lnd_Admin_Info_Update_View.as_view()), # Update Administrative Information

#__ Land Overview __
    path('land-overview-info/su_id=<str:su_id>/', Lnd_Overview_View.as_view()), # Get Land Overview Information
    path('land-overview-info/update/su_id=<str:su_id>/', Lnd_Overview_Update_View.as_view()),

#__ Land Zoning Info __
    path('lnd-zoning-info/su_id=<int:su_id>/', Lnd_Zoning_View.as_view()),
    path('lnd-zoning-info/update/su_id=<int:su_id>/', Lnd_Zoning_Update_View.as_view()),

#__ Land Physical/Environmental Info __
    path('lnd-physical-env/su_id=<int:su_id>/', Lnd_Physical_Env_View.as_view()),
    path('lnd-physical-env/update/su_id=<int:su_id>/', Lnd_Physical_Env_Update_View.as_view()),

#__ RRR Restriction Sub-entries __
    path('rrr-restrictions/rrr_id=<int:rrr_id>/', RRR_Restriction_View.as_view()),

#__ RRR Responsibility Sub-entries __
    path('rrr-responsibilities/rrr_id=<int:rrr_id>/', RRR_Responsibility_View.as_view()),

#__ RRR Extra Documents __
    path('rrr-add-document/ba_unit_id=<int:ba_unit_id>/', RRR_Add_Document_View.as_view()),
    path('rrr-remove-document/<int:doc_link_id>/', RRR_Remove_Document_View.as_view()),

#__ Land Utinet Info __
    path('lnd-utinet-info/su_id=<int:su_id>/', Lnd_Utility_Network_Info_View.as_view()), # Get Utility Network Information
    path('lnd-utinet-info/update/su_id=<int:su_id>/', Lnd_Utility_Network_Info_Update_View.as_view()), # Update Utility Network Information


#__ Building Summary Info __
    path('bld-summary/su_id=<str:su_id>/', Bld_Summary_View.as_view()),

#__ Building Admin Info __
    path('bld-admin-info/su_id=<str:su_id>/', Bld_Admin_Info_View.as_view()),
    path('bld-admin-info/update/su_id=<str:su_id>/', Bld_Admin_Info_Update_View.as_view()),

#__ Building Overview __
    path('bld-overview-info/su_id=<str:su_id>/', Bld_Overview_View.as_view()), # Get Land Overview Information
    path('bld-overview-info/update/su_id=<str:su_id>/', Bld_Overview_Update_View.as_view()),

#__ Building Utinet Info __
    path('bld-utinet-info/su_id=<int:su_id>/', Bld_Utility_Network_Info_View.as_view()),
    path('bld-utinet-info/update/su_id=<int:su_id>/', Bld_Utility_Network_Info_Update_View.as_view()),


#__ Tax & Assessment Info __
    path('tax-assess-info/su_id=<int:su_id>/', Tax_Assessment_View.as_view()), # Get Tax & Assessment Information
    path('tax-assess-info/update/su_id=<int:su_id>/', Tax_Assessment_Update_View.as_view()),

#__ Assessment Ward List __
    path('assess_ward_lst/', Assessment_Ward_View.as_view()), # for GET and POST DATA
    path('assess_ward_update/id=<int:pk>/', Assessment_Ward_Update_View.as_view()), 

#__ Attrib Image Upload __
    path('attrib-image-upload/', Attrib_Image_Upload_View.as_view()),
    path('attrib-image-retrive/su_id=<int:ver_suid>/', Attrib_Image_Retrive_View.as_view()),
    path('attrib-image-delete/su_id=<int:su_id>/', Attrib_Image_Delete_View.as_view()),

#__ Residence Info __
    path('residence-info/', Residence_Info_View.as_view()),

#__ LA_LS_Apt_Unit __
    path('la-ls-apt-unit/', LA_LS_Apt_Unit_View.as_view()),

#__ LA_LS_Utinet_AU __
    path('la-ls-utinet-au/', LA_LS_Utinet_AU_View.as_view()),

#__ LA_LS_Ils_Unit __
    path('la-ls-ils-unit/', LA_LS_Ils_Unit_View.as_view()),

#__ LA_LS_Utinet_Ils __
    path('la-ls-utinet-ils/', LA_LS_Utinet_Ils_View.as_view()),

#__ LA_Spatial_Unit_Sketch_Ref __
    path('la-ls-spatial-unit-sketch-ref/', LA_Spatial_Unit_Sketch_Ref_View.as_view()),


#__ SL_Org_Area_Parent_Bndry __ NOT Used
    path('sl-org-area-parent-bndry/', SL_Org_Area_Parent_Bndry_View.as_view()),

#__ SL_Org_Area_Child_Bndry __ NOT Used
    path('sl-org-area-child-bndry/', SL_Org_Area_Child_Bndry_View.as_view()),

#__ History_Spartialunit_Attrib __
    # path('history-spartialunit-attrib/', History_Spartialunit_Attrib_View.as_view()),
    path('history-spartialunit-attrib-fieldname/<int:suid>/', History_Spartialunit_Attrib_View_Filter_field_name.as_view()), # get field_name list
    path('history-spartialunit-attrib-data/<int:suid>/<str:fieldname>/', History_Spartialunit_Attrib_View_Filter_SuId_FieldName.as_view()),
    path('history-spartialunit-attrib-org_lvl/<int:suid>/<str:fieldname>/', History_Spartialunit_Attrib_View_org.as_view()),
    path('history-spartialunit-attrib-username/', History_Spartialunit_Attrib_View_Filter_username.as_view()),

#__ LA_Spatial_Source Unit __
    path('la-spatial-source/', LA_Spatial_Source_View.as_view()),
    path('la-spatial-source-retrive/su_id=<int:ver_suid>/', LA_Spatial_Source_Retrive_View.as_view()),
    path('la-spatial-source-update/su_id=<int:su_id>/', LA_Spatial_Source_Update_View.as_view()),

#__ LA_SP_Fire_Rescue __
    path('la-sp-fire-rescue/', LA_SP_Fire_Rescue_View.as_view()),

#__ Geom Edit History Info __
    path('geom-edit-history/su_id=<int:ver_suid>/', Geom_Edit_History_View.as_view()),

#__ Messages __
    path('messages/', Messages_View.as_view()),

#__ Inquiries __
    path('inquiries/', Inquiries_View.as_view()),

#__ Reminders __
    path('reminders/', Reminders_View.as_view()),

#__ Tags __
    path('tags/', Tags_View.as_view()),

#__ Dynamic Attributes (Land Tab custom fields) __
    path('dynamic-attribute/', Dynamic_Attribute_View.as_view()),                   # GET (list) + POST (create)
    path('dynamic-attribute/<int:pk>/', Dynamic_Attribute_Delete_View.as_view()),   # DELETE
    path('dynamic-attribute-value/', Dynamic_Attribute_Value_View.as_view()),       # POST (update value)

#__ ba_unit_id from ba_unit_table __
    path('ba-unit-id/su_id=<int:su_id>/', SL_BA_Unit_ID_View.as_view()),

#__ RRR Data __
    path('rrr_data_save/', RRR_Data_Save_View.as_view()),
    path('rrr_data_get/', RRR_Data_get_View.as_view()), # Get API (ex: /rrr_data_get/?su_id=50)

    path('ba_unit/update/<int:ba_unit_id>/', SL_BA_Unit_Update_View.as_view()), # for Delete RRR record "status = False"
    path('rrr/update/<int:ba_unit_id>/', RRR_Update_View.as_view()),  # PATCH existing RRR entry

    path('admin-source/file/<int:admin_source_id>/', DownloadAdminSourcePDF.as_view(), name='download_admin_pdf'),
    path('admin-source/update/<int:admin_source_id>/', AdminSourceUpdateView.as_view()),



#__ SL Rights Activity __
    # path('sl-rights-activity/<int:userID>/', SL_Rights_Activity_View.as_view()),

#__ LA Mortgage Activity __
    # path('la-mortgage-activity/<int:userID>/', LA_Mortgage_Activity_View.as_view()),

#__ LA Responsibility Activity __
    # path('la-responsibility-activity/<int:userID>/', LA_Responsibility_Activity_View.as_view()),

#__ Admin Annotation Activity __
    # path('admin-annotation-activity/<int:userID>/', Admin_Annotation_Activity_View.as_view()),

#__ SL Admin Restrict Activity __
    # path('sl-admin-restrict-activity/<int:userID>/', SL_Admin_Restrict_Activity_View.as_view()),

#__ SL Rights & Liabilities Activity __
    # path('sl-rights-lib-activity/<int:userID>/', SL_Rights_Liabilities_Activity_View.as_view()),

#__ Ownership History Info __
    # path('ownership-history/su_id=<int:ver_suid>/', Ownership_History_View.as_view()),

#__ Mortgage History Info __
    # path('mortgage-history/su_id=<int:ver_suid>/', Mortgage_History_View.as_view()),


#__ Import Vector DATA __
    # path('import_vector_data/', Import_VectorDATA_View.as_view()), # vector data post
    # path('import_vector_data_list/', Import_VectorDATA_List_View.as_view()), # get vector data list
    # path('import_vector_data/id=<int:id>/', Import_VectorDATA_View_Filter.as_view()), # get vector data by record id
    # path('import_vector_data/delete/id=<int:pk>/', Import_VectorDATA_View_delete.as_view()), # delete vector data

#__ Import Raster DATA __
    # path('import_raster_data/', Upload_RasterData_View.as_view()),
    # path('raster_data_list/', RasterData_List_View.as_view()),

    # path('raster_metadata/<int:id>/', Raster_Meta_data_View.as_view()), # Retrieve Raster Meta Data
    # path('raster_download/<int:id>/', Raster_File_Download_View.as_view()), #Retrieve Raster File


#__ Assessment __
    # path('assessment/', Assessment_View.as_view()),

#__ Tax_Info __
    # path('tax-info/', Tax_Info_View.as_view()),

#__ LA Spatial Unit __
    # path('la-spatial-unit/', LA_Spatial_Unit_View.as_view()),

#__ LA_LS_Land_Unit __
    # path('la-ls-land-unit/', LA_LS_Land_Unit_View.as_view()),


#__ LA_LS_Build_Unit __
    # path('la-ls-build-unit/', LA_LS_Build_Unit_View.as_view()),

#__ LA_LS_Utinet_BU __
    # path('la-ls-utinet-bu/', LA_LS_Utinet_BU_View.as_view()),

#__ LA_LS_Ols_Unit __
    # path('la-ls-ols-polygon-unit/', LA_LS_Ols_Polygon_Unit_View.as_view()),
    # path('la-ls-ols-pointline-unit/', LA_LS_Ols_PointLine_Unit_View.as_view()),

#__ LA_LS_MyLayer_Unit __
    # path('la-ls-mylayer-polygon-unit/', LA_LS_MyLayer_Polygon_Unit_View.as_view()),
    # path('la-ls-mylayer-pointline-unit/', LA_LS_MyLayer_PointLine_Unit_View.as_view()),

#__ LA_LS_Utinet_Ols __
    # path('la-ls-utinet-ols/', LA_LS_Utinet_Ols_View.as_view()),

#__ SL Rights & Liabilities __ RRR
    # path('sl-rights-lib/', SL_Rights_Liabilities_View.as_view()),

#__ Admin Annotation __ RRR
    # path('admin-annotation/', Admin_Annotation_View.as_view()),

#__ SL Admin Restrict __ RRR
    # path('sl-admin-res/', SL_Admin_Restrict_View.as_view()),

#__ LA Mortgage __ RRR
    # path('la-mortgage/', LA_Mortgage_View.as_view()),

#__ SL Rights __ RRR
    # path('sl-rights/', SL_Rights_View.as_view()),

#__ LA Responsibility __ RRR
    # path('la-responsibility/', LA_Responsibility_View.as_view()),

#__ LA RRR __ RRR
    # path('la-rrr/', LA_RRR_View.as_view()),

#__ LA Admin Source __ RRR
    # path('la-admin-source/', LA_Admin_Source_View.as_view()),
    path('user-admin-source-activity/<str:userID>/', User_Admin_Source_Activity_View.as_view()),

#__ Ownership Rights Info (Land / Building Tenure) __ RRR
    # path('ownership-rights-info/su_id=<int:ver_suid>/', Ownership_Rights_View.as_view()),

#__ Admin_Sources_RRR_Rights __ RRR
    # path('admin-sources-rrr-rights-info/su_id=<int:su_id>/', LA_Admin_Source_RRR_Rights_View.as_view()),

#__ LADM M:M – BAUnit ↔ SpatialUnit __
    path('ba-unit-spatial-unit/ba_unit_id=<int:ba_unit_id>/', LA_BAUnit_SpatialUnit_View.as_view()),

]


from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.SECURE_MEDIA_URL, document_root=settings.SECURE_MEDIA_ROOT)