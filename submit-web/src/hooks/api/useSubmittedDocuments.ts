import { Submission, SubmittedDocument } from "@/models/Submission";
import { submitRequest } from "@/utils/axiosUtils";
import { queryOptions, useQuery } from "@tanstack/react-query";
import { defaultUseQueryOptions, QUERY_KEY } from "./constants";

type GetProjectsByParamsForStaff = {
  searchOptions?: Record<string, string | number | string[]>;
};
const getDocumentsForStaff = ({
  searchOptions,
}: GetProjectsByParamsForStaff) => {
  const url = "/documents";

  return submitRequest<SubmittedDocument[]>({
    url,
    params: searchOptions,
  });
};

type UseGetDocumentsForStaffParams = {
  searchOptions?: Record<string, string | number | string[]>;
};

export const getSubmittedDocumentsForStaffQueryOptions = ({
  searchOptions,
}: UseGetDocumentsForStaffParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.ACCOUNT_PROJECTS, searchOptions],
    queryFn: () => getDocumentsForStaff({ searchOptions }),
    ...defaultUseQueryOptions,
  });

export const useGetSubmittedDocumentsForStaff = ({
  searchOptions,
}: UseGetDocumentsForStaffParams) => {
  const options = getSubmittedDocumentsForStaffQueryOptions({ searchOptions });
  return useQuery(options);
};

export const getSubmittedDocumentsByPackageIdForStaffQueryOptions = ({
  packageId,
}: {
  packageId: string;
}) =>
  queryOptions({
    queryKey: [QUERY_KEY.PACKAGE_DOCUMENT_SUBMISSIONS, packageId],
    queryFn: () =>
      submitRequest<Submission[]>({
        url: `/documents/submissions/packages/${packageId}`,
      }),
    staleTime: 0,
  });
