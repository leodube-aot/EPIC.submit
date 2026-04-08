import { SubmissionItem } from "@/models/SubmissionItem";
import { submitRequest } from "@/utils/axiosUtils";
import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { QUERY_KEY } from "./constants";
import { SubmissionReview } from "@/models/SubmissionReview";

type GetSubmissionItemByIdParams = {
  itemId: number;
};
const getSubmissionItemById = ({ itemId }: GetSubmissionItemByIdParams) => {
  return submitRequest<SubmissionItem>({
    url: `items/${itemId}`,
  });
};

type UseGetSubmissionItemByIdParams = {
  itemId: number;
  enabled?: boolean;
};

export const getSubmissionItemQueryOptions = ({
  itemId,
  enabled = true,
}: UseGetSubmissionItemByIdParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.SUBMISSION_ITEM, itemId],
    queryFn: () => getSubmissionItemById({ itemId }),
    enabled: enabled && Boolean(itemId),
  });

export const useGetSubmissionItem = ({
  itemId,
  enabled = true,
}: UseGetSubmissionItemByIdParams) => {
  const options = getSubmissionItemQueryOptions({ itemId, enabled });
  return useQuery(options);
};

type GetSubmissionItemByIdForStaffParams = {
  itemId: number;
};
const getSubmissionItemByIdForStaff = ({
  itemId,
}: GetSubmissionItemByIdForStaffParams) => {
  return submitRequest<SubmissionItem>({
    url: `items/${itemId}`,
  });
};

type UseGetSubmissionItemByIdForStaffParams = {
  itemId: number;
  enabled?: boolean;
};

export const getSubmissionItemForStaffQueryOptions = ({
  itemId,
  enabled = true,
}: UseGetSubmissionItemByIdForStaffParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.SUBMISSION_ITEM, itemId],
    queryFn: () => getSubmissionItemByIdForStaff({ itemId }),
    enabled: enabled && Boolean(itemId),
  });

export const useGetSubmissionItemForStaff = ({
  itemId,
  enabled = true,
}: UseGetSubmissionItemByIdForStaffParams) => {
  const options = getSubmissionItemForStaffQueryOptions({ itemId, enabled });
  return useQuery(options);
};

type SaveReviewRequestBody = {
  status?: string;
  form_answers: Record<string, unknown>;
};
export const saveSubmissionReview = (
  itemId: number,
  data: SaveReviewRequestBody,
) => {
  return submitRequest<SubmissionReview>({
    url: `/items/${itemId}/review`,
    method: "post",
    data,
  });
};

type UseSaveSubmissionParams = {
  itemId: number;
  packageId: number;
  accountProjectId: number;
};
export const useSaveSubmissionReview = ({
  itemId,
  packageId,
  accountProjectId,
}: UseSaveSubmissionParams) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SaveReviewRequestBody) =>
      saveSubmissionReview(itemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.SUBMISSION_ITEM, itemId],
      });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.SUBMISSION_PACKAGE, packageId],
      });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.ACCOUNT_PROJECT, accountProjectId],
      });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.SUBMISSION_VERSIONS, accountProjectId],
      });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.PACKAGE_VERSIONS],
      });

      queryClient.removeQueries({
        queryKey: [QUERY_KEY.ACCOUNT_PROJECTS],
      });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.ACTIVITY_LOGS],
      });
    },
  });
};
