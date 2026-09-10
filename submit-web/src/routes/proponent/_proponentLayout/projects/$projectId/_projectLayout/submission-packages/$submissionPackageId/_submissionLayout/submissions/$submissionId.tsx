import { ContentBoxSkeleton } from "@/components/Shared/Layouts/ContentBox/ContentBoxSkeleton";
import { PageGrid } from "@/components/Shared/PageGrid";
import { notify } from "@/components/Shared/Snackbar/snackbarStore";
import {
  ProponentItemForm,
  ProponentItemUpdateForm,
} from "@/components/App/SubmissionItem/ItemForm/ProponentItemForm";
import { getSubmissionItemQueryOptions } from "@/hooks/api/useItems";
import { getSubmissionPackageQueryOptions } from "@/hooks/api/usePackages";
import { SubmissionItemMethod } from "@/models/SubmissionItem";
import { MANAGEMENT_PLAN_RELATED_TYPES } from "@/models/Package";
import { UPDATE_REQUEST_STATUS } from "@/models/UpdateRequest";
import { getSubmissionItemLabel } from "@/utils";
import { HTTP_STATUS } from "@/utils/constants";
import { useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute, Navigate, notFound } from "@tanstack/react-router";
import { isAxiosError } from "axios";

const LoadingSkeleton = () => (
  <PageGrid>
    <ContentBoxSkeleton />
  </PageGrid>
);
export const Route = createFileRoute(
  "/proponent/_proponentLayout/projects/$projectId/_projectLayout/submission-packages/$submissionPackageId/_submissionLayout/submissions/$submissionId",
)({
  component: Submission,
  loader: async ({ context: { queryClient }, params: { submissionId } }) =>
    queryClient.ensureQueryData(
      getSubmissionItemQueryOptions({ itemId: Number(submissionId) }),
    ),
  onError: (error) => {
    if (
      isAxiosError(error) &&
      error.response?.status === HTTP_STATUS.NOT_FOUND
    ) {
      throw notFound();
    }
    notify.error("Failed to load submission item");
    throw error;
  },
  pendingMs: 0,
  pendingComponent: LoadingSkeleton,
  head: ({ loaderData: submissionItem }) => ({
    meta: [{ title: getSubmissionItemLabel(submissionItem?.type.name) }],
  }),
});

export function Submission() {
  const {
    submissionId: subItemId,
    submissionPackageId,
    projectId,
  } = Route.useParams();
  const { data: submissionItem, isLoading: isItemLoading } = useSuspenseQuery(
    getSubmissionItemQueryOptions({ itemId: Number(subItemId) }),
  );
  const { data: submissionPackage, isLoading: isPackageLoading } =
    useSuspenseQuery(
      getSubmissionPackageQueryOptions({
        packageId: Number(submissionPackageId),
      }),
    );

  const hasPackageUpdateRequest =
    submissionPackage?.update_requests.filter(
      (updateRequest) =>
        updateRequest.status !== UPDATE_REQUEST_STATUS.ACCEPTED.value &&
        updateRequest.active,
    ).length > 0;
  const isPackageSubmitted = submissionPackage?.submitted_on;

  const isFormSubmission =
    submissionItem.type.submission_method ===
    SubmissionItemMethod.FORM_SUBMISSION;

  if (isItemLoading || isPackageLoading) {
    return <LoadingSkeleton />;
  }

  const isManagementPlan =
    MANAGEMENT_PLAN_RELATED_TYPES.includes(submissionPackage.type.name);

  if (
    isPackageSubmitted &&
    !hasPackageUpdateRequest &&
    !isFormSubmission &&
    isManagementPlan
  ) {
    return (
      <Navigate
        to={`/proponent/projects/${projectId}/submission-packages/${submissionPackageId}`}
      />
    );
  }

  if (!submissionItem) {
    notify.error("Failed to load submission item");
    return <Navigate to="/error" />;
  }

  return (
    <PageGrid>
      {isPackageSubmitted ? (
        <ProponentItemUpdateForm submissionItem={submissionItem} />
      ) : (
        <ProponentItemForm submissionItem={submissionItem} />
      )}
    </PageGrid>
  );
}
