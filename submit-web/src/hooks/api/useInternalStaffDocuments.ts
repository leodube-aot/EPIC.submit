import { submitRequest } from "@/utils/axiosUtils";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Options } from "./types";
import { InternalStaffDocument } from "@/models/SubmissionItem";
import { QUERY_KEY } from "./constants";

type CreateInternalStaffDocumentFormType = {
  package_id: number;
  document: Partial<InternalStaffDocument>;
};
export const createInternalStaffDocument = ({
  package_id,
  document,
}: CreateInternalStaffDocumentFormType) => {
  return submitRequest<InternalStaffDocument>({
    url: `/internal-staff-documents/packages/${package_id}`,
    method: "post",
    data: document,
  });
};

type UseCreateInternalStaffDocumentProps = {
  packageId: number;
  options?: Options;
};
export const useCreateInternalStaffDocument = ({
  packageId,
  options,
}: UseCreateInternalStaffDocumentProps) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createInternalStaffDocument,
    ...options,
    onSuccess: () => {
      if (options?.onSuccess) {
        options.onSuccess();
      }
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.SUBMISSION_PACKAGE, packageId],
      });
    },
  });
};

type DeleteInternalStaffDocumentProps = {
  documentId: number;
};
export const deleteInternalStaffDocument = ({
  documentId,
}: DeleteInternalStaffDocumentProps) => {
  return submitRequest<void>({
    url: `/internal-staff-documents/packages/${documentId}`,
    method: "delete",
  });
};

type UseDeleteInternalStaffDocumentProps = {
  itemId: number;
  packageId: number;
  options?: Options;
};
export const useDeleteInternalStaffDocument = ({
  itemId,
  packageId,
  options,
}: UseDeleteInternalStaffDocumentProps) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteInternalStaffDocument,
    ...options,
    onSuccess: () => {
      if (options?.onSuccess) {
        options.onSuccess();
      }
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.SUBMISSION_ITEM, itemId],
      });
      queryClient.invalidateQueries({
        queryKey: [QUERY_KEY.SUBMISSION_PACKAGE, packageId],
      });
    },
  });
};
