import { MANAGEMENT_PLAN_RELATED_TYPES, SubmissionPackage } from "@/models/Package";
import { Grid, Stack, Typography } from "@mui/material";
import { BCDesignTokens } from "epic.theme";
import { get, isArray } from "lodash";
import { useMemo } from "react";
import VersionGroup from "@/components/App/Submission/VersionGroup";
import { SubmissionHistory } from "@/components/App/Submission/InfoBox/SubmissionHistory";
import { Else, If, Then } from "react-if";
import dateUtils from "@/utils/dateUtils";

type InfoBoxProps = {
  submissionPackage: SubmissionPackage;
};

export const InfoBox = ({
  submissionPackage
}: InfoBoxProps) => {
  const { version } = submissionPackage;
  const condition = useMemo(() => {
    if (!submissionPackage.meta) return "";
    const mainCondition = get(submissionPackage, "meta.main_condition");
    return get(mainCondition, "condition_number", "");
  }, [submissionPackage]);

  const supportingConditions = useMemo(() => {
    if (!submissionPackage.meta) return "";
    const conditions = get(submissionPackage, "meta.supporting_conditions");
    if (!conditions || !isArray(conditions)) return "";

    return conditions
      .map((condition) => condition.condition_number)
      .filter(Boolean)
      .join(", ");
  }, [submissionPackage]);

  return (
    <>
      {submissionPackage.description && (
        <Grid
          container
          sx={{
            borderRadius: "4px",
            border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
            p: "16px",
            backgroundColor: BCDesignTokens.surfaceColorBackgroundWhite,
            mb: "16px",
          }}
        >
          <Typography
            component="span"
            sx={{
              fontWeight: 700,
              fontSize: "16px",
              lineHeight: "27.008px",
              color: BCDesignTokens.typographyColorPrimary,
            }}
          >
            Description: &nbsp;
            <br />
          </Typography>
          <Typography
            component="span"
            sx={{
              fontWeight: 400,
              fontSize: "16px",
              lineHeight: "27.008px",
              color: BCDesignTokens.typographyColorPrimary,
            }}
          >
            {submissionPackage.description}
          </Typography>
        </Grid>
      )}
      <Grid
        container
        sx={{
          borderRadius: "4px",
          border: `1px solid ${BCDesignTokens.surfaceColorBorderDefault}`,
          p: "16px",
          justifyContent: "space-between",
        }}
      >
        <If
          condition={
            MANAGEMENT_PLAN_RELATED_TYPES.includes(submissionPackage.type.name)
          }
        >
          <Then>
            <Grid item xs={12} md={6} container>
              <Grid item xs={12}>
                <Stack direction={"row"} spacing={2}>
                  <Typography color={BCDesignTokens.themeGray70}>
                    Condition:
                  </Typography>
                  <Typography color={"inherit"}>{condition || "-"}</Typography>
                </Stack>
              </Grid>

              <Grid item xs={12}>
                <Stack direction={"row"} spacing={2}>
                  <Typography color={BCDesignTokens.themeGray70}>
                    Supporting Condition(s):
                  </Typography>
                  <Typography color={"inherit"}>
                    {supportingConditions || "-"}
                  </Typography>
                </Stack>
              </Grid>
            </Grid>
          </Then>
          <Else>
            <Stack
              gap={2}
              sx={{
                display: "flex",
                flexDirection: "row",
              }}
            >
              <Stack direction={"row"} spacing={1}>
                <Typography color={BCDesignTokens.themeGray70}>
                  Submitted on:
                </Typography>
                <Typography color={"inherit"}>
                  {dateUtils.formatDate(submissionPackage.submitted_on) || "-"}
                </Typography>
              </Stack>
            <Stack direction={"row"} spacing={1}>
              <Typography color={BCDesignTokens.themeGray70}>
                Submitted by:
              </Typography>
              <Typography color={"inherit"}>
                {submissionPackage.submitted_by || "-"}
              </Typography>
            </Stack>
          </Stack>
          </Else>
        </If>
            <>
              {version && (
                <Grid
                  item
                  md={6}
                  xs={12}
                  container
                  alignContent={{ xs: "flex-start" }}
                  justifyContent={{ xs: "flex-end" }}
                >
                  <VersionGroup currentPackageVersion={version} />
                </Grid>
              )}
              <Grid item xs={12} container mt={"16px"}>
                <SubmissionHistory
                  submissionPackageId={String(
                    version?.original_package_id ?? submissionPackage.id
                  )}
                />
              </Grid>
            </>
      </Grid>
    </>
  );
};
