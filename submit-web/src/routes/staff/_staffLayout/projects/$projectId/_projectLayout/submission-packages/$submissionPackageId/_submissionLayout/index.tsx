import { PackageStatusChipStack } from "@/components/App/PackageStatusChip/PackageStatusChipStack";
import { EnforceableBanner } from "@/components/App/Submission/EnforceableBanner/EnforceableBanner";
import { useStaffEnforceableBanner } from "@/components/App/Submission/EnforceableBanner/useEnforceableBanner";
import { InfoBox } from "@/components/App/Submission/InfoBox";
import ItemsTable from "@/components/App/Submission/ItemsTable";
import AcknowledgeSubmissionModal from "@/components/App/Submission/Modals/AcknowledgeSubmissionModal";
import ApproveSubmissionModal from "@/components/App/Submission/Modals/ApproveSubmissionModal";
import RefuseSubmissionModal from "@/components/App/Submission/Modals/RefuseSubmissionModal";
import { usePackageTableStore } from "@/components/App/Submission/packageTableStore";
import { SubmissionTitle } from "@/components/App/Submission/SubmissionTitle";
import { SectionUpdateRequestPanel } from "@/components/App/SubmissionItem/SectionUpdateRequestPanel";
import { ContentBox } from "@/components/Shared/Layouts/ContentBox";
import { LoadingButton as Button } from "@/components/Shared/LoadingButton";
import { SubmitLoaderBackdrop } from "@/components/Shared/Overlays/SubmitLoaderBackdrop";
import { PageGrid } from "@/components/Shared/PageGrid";
import BarTitle from "@/components/Shared/Text/BarTitle";
import { useMounted } from "@/hooks/common";
import { useManagementPlanName } from "@/hooks/useManagementPlanName";
import { useStaffSubmissionPage } from "@/hooks/useStaffSubmissionPage";
import { useUpdateRequests } from "@/hooks/useUpdateRequests";
import {
  MANAGEMENT_PLAN_RELATED_TYPES,
  PACKAGE_STATUS,
  SubmissionPackageType,
} from "@/models/Package";
import { Box, Grid, Typography } from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import {
  createFileRoute,
  Navigate,
  useNavigate,
  useParams,
} from "@tanstack/react-router";
import { BCDesignTokens } from "epic.theme";

export const Route = createFileRoute(
  "/staff/_staffLayout/projects/$projectId/_projectLayout/submission-packages/$submissionPackageId/_submissionLayout/",
)({
  component: SubmissionPage,
});

export default function SubmissionPage() {
  const { reset } = usePackageTableStore();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const {
    projectId: accountProjectIdParam,
    submissionPackageId: submissionPackageIdParam,
  } = useParams({
    from: Route.id,
  });

  const submissionPackageId = Number(submissionPackageIdParam);
  const accountProjectId = Number(accountProjectIdParam);

  const {
    packageVersions,
    currentPackageVersion,
    accountProject,
    submissionPackage,
    isFetching,
    updatePackageState,
    refusePackage,
    isLoading,
    canAcknowledge,
    showAcknowledgeButton,
    showApproveButtons,
    setOpenModal,
    setCloseModal,
  } = useStaffSubmissionPage({
    submissionPackageId,
    accountProjectId,
    queryClient,
  });

  const { bannerType, hasBanner } = useStaffEnforceableBanner({
    packageVersions,
    currentPackageVersion,
  });

  const {
    pendingRequests,
    previousUpdateRequests,
    sentUpdateRequests,
    openRequestSectionNames,
    handleRequestUpdate,
    handleRemoveRequest,
    handleUpdateNote,
    handleSendRequests,
    handleAcceptUpdate,
    handleWithdrawUpdate,
    isSendingRequests,
  } = useUpdateRequests({
    submissionPackageId,
    submissionPackage,
    accountProjectId,
    queryClient,
  });

  const managementPlanName = useManagementPlanName(submissionPackage);

  // Withdrawing an open update request is not permitted for certain package
  // types (e.g. Management Plans, IEM).
  const canWithdrawUpdate =
    !!submissionPackage?.type?.name &&
    !MANAGEMENT_PLAN_RELATED_TYPES.includes(
      submissionPackage.type.name,
    );

  useMounted(() => {
    return () => {
      reset();
    };
  });

  const handleAcknowledgeClick = () => {
    setOpenModal(
      <AcknowledgeSubmissionModal
        onConfirm={() => {
          updatePackageState({
            packageId: submissionPackageId,
            data: {
              status: PACKAGE_STATUS.ACKNOWLEDGED.value,
            },
          });
        }}
        onCancel={() => setCloseModal()}
        hasOpenUpdateRequests={sentUpdateRequests.length > 0}
        openRequestSectionNames={openRequestSectionNames}
      />,
    );
  };

  const handleApproveSubmissionClick = () => {
    setOpenModal(
      <ApproveSubmissionModal
        onConfirm={() => {
          updatePackageState({
            packageId: submissionPackageId,
            data: {
              status: PACKAGE_STATUS.APPROVED.value,
            },
          });
        }}
        onCancel={() => setCloseModal()}
        hasOpenUpdateRequests={sentUpdateRequests.length > 0}
        openRequestSectionNames={openRequestSectionNames}
      />,
    );
  };

  const handleNotApprovedClick = () => {
    setOpenModal(
      <RefuseSubmissionModal
        onConfirm={(data) => {
          refusePackage({
            packageId: submissionPackageId,
            data: {
              decision_date: data.decisionDate,
              reason: data.reason,
            },
          });
        }}
        onCancel={() => setCloseModal()}
        hasOpenUpdateRequests={sentUpdateRequests.length > 0}
        openRequestSectionNames={openRequestSectionNames}
      />,
    );
  };

  if (!accountProject || !submissionPackage) {
    return <Navigate to={"/error"} />;
  }

  return (
    <PageGrid>
      <SubmitLoaderBackdrop isOpen={isFetching} />
      <Grid item xs={12}>
        <ContentBox
          mainLabel={accountProject?.project?.name}
          topLabel={accountProject?.project?.proponent?.name || ""}
          bottomLabel={
            accountProject?.project?.ea_certificate
              ? `EAC # ${accountProject?.project?.ea_certificate}`
              : ""
          }
        >
          <Box
            sx={{
              padding: BCDesignTokens.layoutPaddingMedium,
              display: "flex",
              flexDirection: "column",
              borderRadius: "4px",
              border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
              gap: BCDesignTokens.layoutPaddingSmall,
            }}
          >
            <SubmissionTitle
              sx={{ pb: BCDesignTokens.layoutPaddingSmall }}
              submissionPackage={submissionPackage}
            />
            <Box
              sx={{
                pt: BCDesignTokens.layoutPaddingSmall,
                pb: BCDesignTokens.layoutPaddingMedium,
                px: BCDesignTokens.layoutPaddingMedium,
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                borderRadius: "4px",
                border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
              }}
            >
              <Box
                sx={{
                  width: "100%",
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  mb: hasBanner ? 0 : BCDesignTokens.layoutMarginXlarge,
                }}
              >
                <BarTitle title={managementPlanName} />
                <Box flexDirection={"row"} sx={{ display: "flex" }}>
                  <Typography
                    color={BCDesignTokens.themeGray70}
                    fontWeight={900}
                    sx={{ mr: BCDesignTokens.layoutMarginMedium }}
                  >
                    Submission Status:
                  </Typography>
                  <PackageStatusChipStack
                    submissionPackage={submissionPackage}
                  />
                </Box>
              </Box>
              <EnforceableBanner
                bannerType={bannerType}
                enforceableText="This submission is the version the EAO has finalized for implementation."
                notEnforceableText="This version has failed review, or has been replaced with a newer version."
              />
              <InfoBox submissionPackage={submissionPackage} />
              <Box
                sx={{
                  mb: BCDesignTokens.layoutMarginXlarge,
                  pt: BCDesignTokens.layoutPaddingXsmall,
                }}
              >
                <ItemsTable
                  submissionPackage={submissionPackage}
                  accountProject={accountProject}
                  onRequestUpdate={handleRequestUpdate}
                  pendingRequestItemTypeIds={pendingRequests.map(
                    (r) => r.itemTypeId,
                  )}
                  sentRequestItemTypeIds={sentUpdateRequests.map(
                    (r) => r.itemTypeId,
                  )}
                />
              </Box>
              <Box
                sx={{
                  mb: BCDesignTokens.layoutMarginLarge,
                  width: "100%",
                }}
              >
                <SectionUpdateRequestPanel
                  pendingRequests={pendingRequests}
                  sentRequests={sentUpdateRequests}
                  previousRequests={previousUpdateRequests}
                  onRemoveFlag={handleRemoveRequest}
                  onUpdateNote={handleUpdateNote}
                  onSendRequests={handleSendRequests}
                  onAcceptUpdate={handleAcceptUpdate}
                  onWithdrawUpdate={
                    canWithdrawUpdate ? handleWithdrawUpdate : undefined
                  }
                  packageId={Number(submissionPackageId)}
                  isLoading={isSendingRequests}
                />
              </Box>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "flex-end",
                  width: "100%",
                  gap: 2,
                  mt: 4,
                }}
              >
                <Button
                  variant="contained"
                  color="primary"
                  onClick={() =>
                    navigate({ to: `/staff/projects/${accountProject.id}` })
                  }
                  sx={{ ml: "auto" }}
                >
                  Save & Exit
                </Button>
                {showAcknowledgeButton && (
                  <Button
                    variant="outlined"
                    color="primary"
                    onClick={handleAcknowledgeClick}
                    disabled={!canAcknowledge || isLoading}
                    loading={isLoading}
                  >
                    {submissionPackage?.type.name ===
                    SubmissionPackageType.ADDITIONAL_INFORMATION ? (
                      <>
                        Acknowledge Submission <i>(optional)</i>
                      </>
                    ) : (
                      "Acknowledge Submission"
                    )}
                  </Button>
                )}
                {showApproveButtons && (
                  <>
                    <Button
                      variant="outlined"
                      color="error"
                      onClick={handleNotApprovedClick}
                      disabled={isLoading}
                      loading={isLoading}
                    >
                      Not Approved
                    </Button>
                    <Button
                      variant="outlined"
                      color="primary"
                      onClick={handleApproveSubmissionClick}
                      disabled={isLoading}
                      loading={isLoading}
                    >
                      Approve Submission
                    </Button>
                  </>
                )}
              </Box>
            </Box>
          </Box>
        </ContentBox>
      </Grid>
    </PageGrid>
  );
}
