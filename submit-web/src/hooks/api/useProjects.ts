import { AccountProject, Project } from "@/models/Project";
import { submitRequest } from "@/utils/axiosUtils";
import { queryOptions, useMutation, useQuery } from "@tanstack/react-query";
import { Options } from "./types";
import { defaultUseQueryOptions, QUERY_KEY } from "./constants";

interface GetPackagesByAccountIdResponse {
  project_id: string;
  packages: [
    {
      id: number;
      name: string;
      original_package_id: number;
    },
  ];
}

const loadProjectsByProponentId = (proponentId?: number) => {
  if (!proponentId) {
    return Promise.reject(new Error("Proponent ID is required"));
  }
  return submitRequest<Project[]>({
    url: `/projects/proponents/${proponentId}`,
  });
};

const addProjects = ({
  accountId,
  projectIds,
}: {
  accountId: number;
  projectIds: number[];
}) => {
  return submitRequest({
    url: `/projects/accounts/${accountId}`,
    method: "post",
    data: {
      project_ids: projectIds,
    },
  });
};

export const useLoadProjectsByProponentId = (proponentId?: number) => {
  return useQuery({
    queryKey: [QUERY_KEY.PROJECTS, proponentId],
    queryFn: () => loadProjectsByProponentId(proponentId),
    enabled: Boolean(proponentId),
    retry: false,
  });
};

type GetProjectsByAccountParams = {
  accountId?: number;
  searchOptions?: Record<string, string | number | string[]>;
};

const getAccountProjectsByAccountId = ({
  accountId,
  searchOptions,
}: GetProjectsByAccountParams) => {
  // Initialize URL with base path and account ID
  const url = `/projects/accounts/${accountId}`;

  return submitRequest<AccountProject[]>({
    url,
    params: searchOptions,
  });
};

const getAccountPackagesByAccountId = ({
  accountId,
  searchOptions,
}: GetProjectsByAccountParams) => {
  // Initialize URL with base path and account ID
  const url = `/accounts/${accountId}/packages`;

  return submitRequest<GetPackagesByAccountIdResponse[]>({
    url,
    params: searchOptions,
  });
};

export const useAddProjects = (options?: Options) => {
  return useMutation({
    mutationFn: addProjects,
    ...options,
  });
};

type UseGetProjectsByAccountParams = {
  accountId: number | null | undefined;
  searchOptions?: Record<string, string | number | string[]>;
  customQueryOptions?: Record<string, unknown>;
};

export const getAccountProjectsByAccountQueryOptions = ({
  accountId,
  searchOptions,
  customQueryOptions = {},
}: UseGetProjectsByAccountParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.ACCOUNT_PROJECTS, accountId, searchOptions],
    queryFn: () =>
      getAccountProjectsByAccountId({
        accountId: accountId as number,
        searchOptions,
      }),
    enabled: Boolean(accountId),
    ...defaultUseQueryOptions,
    ...customQueryOptions,
  });

export const useGetAccountProjectsByAccount = ({
  accountId,
  searchOptions,
}: UseGetProjectsByAccountParams) => {
  const options = getAccountProjectsByAccountQueryOptions({
    accountId,
    searchOptions,
  });
  return useQuery(options);
};

type GetAccountProjectsByIdParams = {
  accountProjectId: number;
};
const getAccountProjectById = ({
  accountProjectId,
}: GetAccountProjectsByIdParams) => {
  return submitRequest<AccountProject>({
    url: `projects/${accountProjectId}`,
  });
};

type UseGetAccountProjectByIdParams = {
  accountProjectId: number | null | undefined;
};

export const getAccountProjectQueryOptions = (
  accountProjectId?: number | null,
) =>
  queryOptions({
    queryKey: [QUERY_KEY.ACCOUNT_PROJECT, accountProjectId],
    queryFn: () =>
      getAccountProjectById({ accountProjectId: accountProjectId as number }),
    enabled: !!accountProjectId,
    ...defaultUseQueryOptions,
  });

export const useGetAccountProject = ({
  accountProjectId,
}: UseGetAccountProjectByIdParams) => {
  const options = getAccountProjectQueryOptions(accountProjectId);
  return useQuery(options);
};

type GetAccountProjectsByIdForStaffParams = {
  accountProjectId: number;
};
const getAccountProjectByIdForStaff = ({
  accountProjectId,
}: GetAccountProjectsByIdForStaffParams) => {
  return submitRequest<AccountProject>({
    url: `projects/${accountProjectId}`,
  });
};

type UseGetAccountProjectByIdForStaffParams = {
  accountProjectId: number;
};

export const getAccountProjectForStaffQueryOptions = (
  accountProjectId: number,
) =>
  queryOptions({
    queryKey: [QUERY_KEY.ACCOUNT_PROJECT, accountProjectId],
    queryFn: () => getAccountProjectByIdForStaff({ accountProjectId }),
    enabled: Boolean(accountProjectId),
    ...defaultUseQueryOptions,
  });

export const useGetAccountProjectForStaff = ({
  accountProjectId,
}: UseGetAccountProjectByIdForStaffParams) => {
  const options = getAccountProjectForStaffQueryOptions(accountProjectId);
  return useQuery(options);
};

type GetProjectsByParamsForStaff = {
  searchOptions?: Record<string, string | number | string[]>;
  page?: number;
  pageSize?: number;
};

type AccountProjectPage = {
  projects: AccountProject[];
  next_cursor: number;
  total: number;
};
export const getAccountProjectsForStaff = ({
  searchOptions,
  page,
  pageSize,
}: GetProjectsByParamsForStaff) => {
  const url = "/projects";

  return submitRequest<AccountProjectPage>({
    url,
    params: {
      ...searchOptions,
      page: page,
      page_size: pageSize,
    },
  });
};

type UseGetProjectsForStaffParams = {
  searchOptions?: Record<string, string | number | string[]>;
  // queryOptions?: Record<string, unknown>;
};

export const getAccountProjectsForStaffQueryOptions = ({
  searchOptions,
}: UseGetProjectsForStaffParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.ACCOUNT_PROJECTS, searchOptions],
    queryFn: () => getAccountProjectsForStaff({ searchOptions }),
    ...defaultUseQueryOptions,
  });

export const useGetAccountProjectsForStaff = ({
  searchOptions,
}: UseGetProjectsForStaffParams) => {
  const options = getAccountProjectsForStaffQueryOptions({ searchOptions });
  return useQuery(options);
};

export const getAccountPackagesByAccountIdQueryOptions = ({
  accountId,
  searchOptions,
  customQueryOptions = {},
}: UseGetProjectsByAccountParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.ACCOUNT_SUBMISSION_PACKAGES, accountId],
    queryFn: () =>
      getAccountPackagesByAccountId({
        accountId: accountId as number,
        searchOptions,
      }),
    enabled: Boolean(accountId),
    staleTime: 0,
    ...customQueryOptions,
  });

export const useGetAccountPackagesByAccountId = ({
  accountId,
  searchOptions,
}: UseGetProjectsByAccountParams) => {
  const options = getAccountPackagesByAccountIdQueryOptions({
    accountId,
    searchOptions,
  });
  return useQuery(options);
};

const getAccountProjectsByUserId = ({ userId }: { userId: number }) => {
  // Initialize URL with base path and account ID
  const url = `/projects/users/${userId}`;

  return submitRequest<AccountProject[]>({
    url,
  });
};

type UseGetProjectsByUserIdParams = {
  userId: number;
};

export const getAccountProjectsByUserQueryOptions = ({
  userId,
}: UseGetProjectsByUserIdParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.USER_PROJECTS, userId],
    queryFn: () => getAccountProjectsByUserId({ userId }),
    enabled: Boolean(userId),
  });

export const useGetAccountProjectsByUserId = ({
  userId,
}: UseGetProjectsByUserIdParams) => {
  const options = getAccountProjectsByUserQueryOptions({ userId });
  return useQuery(options);
};
