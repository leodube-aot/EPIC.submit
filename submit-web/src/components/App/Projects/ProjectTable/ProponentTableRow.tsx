import dateUtils from "@/utils/dateUtils";
import { Chip, Typography } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import { MANAGEMENT_PLAN_RELATED_TYPES, SubmissionPackage } from "@/models/Package";
import { PackageStatusChipStack } from "@/components/App/PackageStatusChip/PackageStatusChipStack";
import {
  StyledProjectTableCell,
  StyledProjectTableRow,
} from "@/components/App/Projects/ProjectTable/StyledComponents";
import { useNavigate } from "@tanstack/react-router";
import { SubmitLink } from "@/components/Shared/Text/SubmitLink";
import { useManagementPlanName } from "@/hooks/useManagementPlanName";

interface ProjectRowProps {
  subPackage: SubmissionPackage;
}

export default function ProponentTableRow({ subPackage }: ProjectRowProps) {
  const navigate = useNavigate();
  const onSubmissionClick = () => {
    navigate({
      to: `/proponent/projects/${subPackage.account_project_id}/submission-packages/${subPackage.id}`,
    });
  };

  const managementPlanName = useManagementPlanName(subPackage);
  const isMPRelated = MANAGEMENT_PLAN_RELATED_TYPES.includes(subPackage.type.name);
  const conditionNumber = subPackage.meta?.main_condition?.condition_number;

  return (
    <>
      <StyledProjectTableRow>
        {isMPRelated && (
          <StyledProjectTableCell align="left" sx={{ width: "5%" }}>
            {conditionNumber && (
              <Chip
                label={`#${conditionNumber}`}
                size="small"
                variant="outlined"
                sx={{ height: "20px", fontSize: "0.7rem", fontWeight: "bold" }}
              />
            )}
          </StyledProjectTableCell>
        )}
        <StyledProjectTableCell sx={{ width: isMPRelated ? "50%" : "55%" }}>
          <SubmitLink
            sx={{
              display: "flex",
              alignItems: "center",
              color: BCDesignTokens.themeBlue90,
              textDecoration: "none",
              width: "fit-content",
            }}
            onClick={onSubmissionClick}
          >
            <Typography fontSize="1rem" fontWeight="bold" color={BCDesignTokens.themeBlue90}>
              {managementPlanName}
            </Typography>
          </SubmitLink>
        </StyledProjectTableCell>
        <StyledProjectTableCell align="left" width={"15%"}>
          {subPackage.submitted_on
            ? dateUtils.formatDate(subPackage.submitted_on)
            : "-"}
        </StyledProjectTableCell>
        <StyledProjectTableCell align="left" width={"15%"}>
          {subPackage.submitted_by ?? "-"}
        </StyledProjectTableCell>
        <StyledProjectTableCell
          width={"15%"}
          align="right"
          sx={{ pr: BCDesignTokens.layoutPaddingSmall }}
        >
          <PackageStatusChipStack submissionPackage={subPackage} />
        </StyledProjectTableCell>
      </StyledProjectTableRow>
    </>
  );
}
