import { submitRequest } from "@/utils/axiosUtils";
import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { Options } from "./types";
import { PackageVersion, SubmissionPackage } from "@/models/Package";
import { defaultUseQueryOptions, QUERY_KEY } from "./constants";
import { ACTIVITY_LOG_ENTITY_TYPE } from "@/models/ActivityLog";

const createSubmissionPackage = ({
  accountProjectId,
  data,
}: {
  accountProjectId: number;
  data: Record<string, unknown>;
}) => {
  return submitRequest<SubmissionPackage>({
    url: `/packages/account-projects/${accountProjectId}`,
    method: "post",
    data,
  });
};

const createNewPackageVersion = ({
  originalPackageId,
  data,
}: {
  originalPackageId: number;
  data: PackageVersion;
}) => {
  return submitRequest<SubmissionPackage>({
    url: `/packages/${originalPackageId}/versions`,
    method: "post",
    data,
  });
};

export const useCreateSubmissionPackage = (options?: Options) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createSubmissionPackage,
    ...options,
    onSuccess: (submissionPackage) => {
      if (options?.onSuccess) {
        options.onSuccess(submissionPackage);
      }
      queryClient.setQueryData(
        [QUERY_KEY.SUBMISSION_PACKAGE, submissionPackage.id],
        submissionPackage,
      );
      queryClient.invalidateQueries({
        queryKey: [
          QUERY_KEY.ACCOUNT_PROJECT,
          submissionPackage.account_project_id,
        ],
      });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.ACCOUNT_PROJECTS],
      });
    },
  });
};

export const useCreateNewPackageVersion = (options?: Options) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createNewPackageVersion,
    ...options,
    onSuccess: (submissionPackage) => {
      if (options?.onSuccess) {
        options.onSuccess(submissionPackage);
      }
      queryClient.setQueryData(
        [QUERY_KEY.SUBMISSION_PACKAGE, submissionPackage.id],
        submissionPackage,
      );

      queryClient.invalidateQueries({
        queryKey: [
          QUERY_KEY.SUBMISSION_VERSIONS,
          submissionPackage.account_project_id,
        ],
      });

      queryClient.invalidateQueries({
        queryKey: [
          QUERY_KEY.ACCOUNT_PROJECT,
          submissionPackage.account_project_id,
        ],
      });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.ACCOUNT_PROJECTS],
      });

      queryClient.invalidateQueries({
        queryKey: [
          QUERY_KEY.PACKAGE_VERSIONS,
          submissionPackage.version.original_package_id,
        ],
      });

      queryClient.invalidateQueries({
        queryKey: [
          QUERY_KEY.ACTIVITY_LOGS,
          submissionPackage.version.original_package_id,
          ACTIVITY_LOG_ENTITY_TYPE.PACKAGE,
        ],
      });
    },
  });
};

type GetSubmissionPackageByIdParams = {
  packageId: number;
};
export const getSubmissionPackageById = ({
  packageId,
}: GetSubmissionPackageByIdParams) => {
  return submitRequest<SubmissionPackage>({
    url: `packages/${packageId}`,
  });
};

export const getStaffSubmissionPackageById = ({
  packageId,
}: GetSubmissionPackageByIdParams) => {
  return submitRequest<SubmissionPackage>({
    url: `packages/${packageId}`,
  });
};

type UseGetSubmissionPackageByIdParams = {
  packageId: number;
  enabled?: boolean;
};

export const getSubmissionPackageQueryOptions = ({
  packageId,
  enabled = true,
}: UseGetSubmissionPackageByIdParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.SUBMISSION_PACKAGE, packageId],
    queryFn: () => getSubmissionPackageById({ packageId }),
    enabled: enabled && Boolean(packageId),
    ...defaultUseQueryOptions,
  });

export const getStaffSubmissionPackageQueryOptions = ({
  packageId,
  enabled = true,
}: UseGetSubmissionPackageByIdParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.SUBMISSION_PACKAGE, packageId],
    queryFn: () => getStaffSubmissionPackageById({ packageId }),
    enabled: enabled && Boolean(packageId),
    ...defaultUseQueryOptions,
  });

export const useGetSubmissionPackage = ({
  packageId,
  enabled = true,
}: UseGetSubmissionPackageByIdParams) => {
  const options = getSubmissionPackageQueryOptions({ packageId, enabled });
  return useQuery(options);
};

export const useGetStaffSubmissionPackage = ({
  packageId,
  enabled = true,
}: UseGetSubmissionPackageByIdParams) => {
  const options = getStaffSubmissionPackageQueryOptions({ packageId, enabled });
  return useQuery(options);
};

type GetPackageVersionsByOriginalPackageId = {
  originalPackageId?: number;
};
const getPackageVersionsByOriginalPackageId = ({
  originalPackageId,
}: GetPackageVersionsByOriginalPackageId) => {
  return submitRequest<PackageVersion[]>({
    url: `packages/${originalPackageId}/versions`,
  });
};

const addIsLatestFlag = (versions: PackageVersion[]): PackageVersion[] => {
  // Find the latest approved version
  const latestApprovedVersion = versions.find((pv) => pv.is_approved);

  // Find the latest unapproved version that's newer than latest approved
  let latestUnapprovedNewerThanApproved: PackageVersion | undefined;
  if (latestApprovedVersion) {
    latestUnapprovedNewerThanApproved = versions.find(
      (pv) => !pv.is_approved && pv.version > latestApprovedVersion.version,
    );
  }

  return versions.map((pv) => ({
    ...pv,
    is_latest:
      pv.id === latestApprovedVersion?.id ||
      pv.id === latestUnapprovedNewerThanApproved?.id,
  }));
};

type UseGetPackageVersionsByOriginalPackageIdParams = {
  originalPackageId?: number;
  enabled?: boolean;
};
export const getPackageVersionsByOriginalPackageIdQueryOptions = ({
  originalPackageId,
  enabled = true,
}: UseGetPackageVersionsByOriginalPackageIdParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.PACKAGE_VERSIONS, originalPackageId],
    queryFn: () => getPackageVersionsByOriginalPackageId({ originalPackageId }),
    select: (data) => addIsLatestFlag(data),
    enabled: enabled && Boolean(originalPackageId),
  });

export const useGetPackageVersionsByOriginalPackageId = ({
  originalPackageId,
  enabled = true,
}: UseGetPackageVersionsByOriginalPackageIdParams) => {
  const options = getPackageVersionsByOriginalPackageIdQueryOptions({
    originalPackageId,
    enabled,
  });
  return useQuery(options);
};

const updateStateSubmissionPackage = ({
  packageId,
  data,
}: {
  packageId: number;
  data: Record<string, unknown>;
}) => {
  return submitRequest<SubmissionPackage>({
    url: `/packages/${packageId}/state`,
    method: "post",
    data,
  });
};

export const useUpdateStateSubmissionPackage = (options?: Options) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateStateSubmissionPackage,
    ...options,
    onSuccess: (submissionPackage) => {
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.SUBMISSION_PACKAGE, submissionPackage.id],
      });
      queryClient.invalidateQueries({
        queryKey: [
          QUERY_KEY.ACCOUNT_PROJECT,
          submissionPackage.account_project_id,
        ],
      });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.ACCOUNT_PROJECTS],
      });
      queryClient.refetchQueries({
        queryKey: [QUERY_KEY.ACTIVITY_LOGS],
      });
      if (options?.onSuccess) {
        options.onSuccess();
      }
    },
  });
};

const createPackageUpdateRequest = ({
  packageId,
  data,
}: {
  packageId: number;
  data: Record<string, unknown>;
}) => {
  return submitRequest<SubmissionPackage>({
    url: `/packages/${packageId}/update-request`,
    method: "post",
    data,
  });
};

const acceptUpdateRequest = ({
  packageId,
  updateRequestId,
}: {
  packageId: number;
  updateRequestId: number;
}) => {
  return submitRequest<SubmissionPackage>({
    url: `/packages/${packageId}/update-request/${updateRequestId}`,
    method: "patch",
  });
};

type UseCreatePackageUpdateRequestParams = {
  packageId: number;
  accountProjectId: number;
  options?: Options;
};
export const useCreatePackageUpdateRequest = ({
  packageId,
  accountProjectId,
  options = {},
}: UseCreatePackageUpdateRequestParams) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createPackageUpdateRequest,
    ...options,
    onSuccess: (submissionPackage) => {
      if (options?.onSuccess) {
        options.onSuccess();
      }

      queryClient.setQueryData(
        [QUERY_KEY.SUBMISSION_PACKAGE, packageId],
        submissionPackage,
      );
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.ACCOUNT_PROJECT, accountProjectId],
      });
      queryClient.refetchQueries({
        queryKey: [QUERY_KEY.ACCOUNT_PROJECTS],
      });
    },
  });
};

const createPackageUpdateRequesNote = ({
  packageId,
  updateRequestId,
  data,
}: {
  packageId: number;
  updateRequestId: number;
  data: Record<string, unknown>;
}) => {
  return submitRequest<SubmissionPackage>({
    url: `/packages/${packageId}/update-requests/${updateRequestId}/note`,
    method: "post",
    data,
  });
};

type UseAcceptUpdateRequestParams = {
  packageId: number;
  options?: Options;
};
export const useAcceptUpdateRequest = ({
  packageId,
  options = {},
}: UseAcceptUpdateRequestParams) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: acceptUpdateRequest,
    ...options,
    onSuccess: (submissionPackage) => {
      if (options?.onSuccess) {
        options.onSuccess();
      }

      queryClient.setQueryData(
        [QUERY_KEY.SUBMISSION_PACKAGE, packageId],
        submissionPackage,
      );
    },
  });
};

type UseCreatePackageUpdateRequestNoteParams = {
  packageId: number;
  options?: Options;
};
export const useCreatePackageUpdateRequesNote = ({
  packageId,
  options = {},
}: UseCreatePackageUpdateRequestNoteParams) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createPackageUpdateRequesNote,
    ...options,
    onSuccess: (submissionPackage) => {
      if (options?.onSuccess) {
        options.onSuccess();
      }

      queryClient.setQueryData(
        [QUERY_KEY.SUBMISSION_PACKAGE, packageId],
        submissionPackage,
      );
    },
  });
};
