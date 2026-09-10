import { ContentBox } from "@/components/Shared/Layouts/ContentBox";
import { AccountProject } from "@/models/Project";
import { MANAGEMENT_PLAN_RELATED_TYPES } from "@/models/Package";
import { USER_TYPE } from "@/models/User";
import { useAccount } from "@/store/accountStore";
import { useNavigate } from "@tanstack/react-router";
import { ProjectSubmissionsCard } from "./ProjectSubmissionsCard";
import { PROJECT_STATUS } from "@/components/Shared/ProjectStatus/constants";
import { useMemo } from "react";

type ProjectParam = {
  accountProject: AccountProject;
};

export const Project = ({ accountProject }: ProjectParam) => {
  const navigate = useNavigate();
  const { userType } = useAccount();

  const is_proponent = useMemo(() => userType === USER_TYPE.PROPONENT, [userType]);
  const { name, ea_certificate } = accountProject.project;
  const hasAccountProjectWorks =
    (accountProject.account_project_works?.length ?? 0) > 0;

  const handleNewSubmission = (workId?: number, isManagementPlan?: boolean) => {
    navigate({
      to: `/proponent/projects/${accountProject.id}/new-submission`,
      search: { workId, isManagementPlan },
    });
  };

  return (
    <ContentBox
      data-testid={`project-${accountProject.id}`}
      mainLabel={name}
      topLabel={accountProject.project.proponent?.name || ""}
      bottomLabel={ea_certificate ? `EAC # ${ea_certificate}` : ""}
    >
      {hasAccountProjectWorks &&
        accountProject.account_project_works &&
        accountProject.account_project_works.map((accountProjectWork) => {
          const workPackages = accountProject.packages.filter(
            (pkg) => pkg.account_project_work?.id === accountProjectWork.id,
          );
          return (
            <ProjectSubmissionsCard
              key={accountProjectWork.id}
              title={accountProjectWork.work.title || ""}
              status={
                accountProjectWork.work.current_phase?.name ||
                PROJECT_STATUS.POST_DECISION
              }
              isWorkRelated={true}
              workId={accountProjectWork.id}
              packages={workPackages}
              onNewSubmission={handleNewSubmission}
            />
          );
        })}
        {((is_proponent && accountProject.project.has_approved_condition) ||
          (!is_proponent &&
            accountProject.packages.some((pkg) =>
              MANAGEMENT_PLAN_RELATED_TYPES.includes(pkg.type.name),
            ))) && (
          <ProjectSubmissionsCard
            title="Management Plans & Related Documents"
            status={PROJECT_STATUS.POST_DECISION}
            isWorkRelated={false}
            packages={accountProject.packages.filter((pkg) =>
              MANAGEMENT_PLAN_RELATED_TYPES.includes(pkg.type.name),
            )}
            onNewSubmission={handleNewSubmission}
          />
        )}
    </ContentBox>
  );
};
