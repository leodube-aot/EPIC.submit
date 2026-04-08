import { ActivityLog } from "@/models/ActivityLog";
import { submitRequest } from "@/utils/axiosUtils";
import { queryOptions, useQuery } from "@tanstack/react-query";
import { QUERY_KEY } from "./constants";

type GetActivityLogForAdminByIdParams = {
  id: number;
  entityType: string;
};
const getActivityLogForAdminById = ({
  id,
  entityType,
}: GetActivityLogForAdminByIdParams) => {
  return submitRequest<ActivityLog[]>({
    url: `activity-logs/${entityType}/${id}`,
  });
};

type UseGetActivityLogForAdminByIdParams = {
  id: number;
  entityType: string;
  enabled?: boolean;
};

export const getActivityLogForAdminQueryOptions = ({
  id,
  entityType,
  enabled = true,
}: UseGetActivityLogForAdminByIdParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.ACTIVITY_LOGS, id, entityType],
    queryFn: () => getActivityLogForAdminById({ id, entityType }),
    enabled: enabled && Boolean(id) && Boolean(entityType),
    retry: false,
  });

export const useGetActivityLogForAdmin = ({
  id,
  entityType,
  enabled = true,
}: UseGetActivityLogForAdminByIdParams) => {
  const options = getActivityLogForAdminQueryOptions({
    id,
    entityType,
    enabled,
  });
  return useQuery(options);
};

// Add a new function for proponent users
const getActivityLogForProponentById = ({
  id,
  entityType,
}: GetActivityLogForAdminByIdParams) => {
  return submitRequest<ActivityLog[]>({
    url: `activity-logs/${entityType}/${id}`,
  });
};

// Add query options for proponent endpoint
export const getActivityLogForProponentQueryOptions = ({
  id,
  entityType,
  enabled = true,
}: UseGetActivityLogForAdminByIdParams) =>
  queryOptions({
    queryKey: [QUERY_KEY.ACTIVITY_LOGS, id, entityType],
    queryFn: () => getActivityLogForProponentById({ id, entityType }),
    enabled: enabled && Boolean(id) && Boolean(entityType),
    retry: false,
  });

// Add hook for proponent users
export const useGetActivityLogForProponent = ({
  id,
  entityType,
  enabled = true,
}: UseGetActivityLogForAdminByIdParams) => {
  const options = getActivityLogForProponentQueryOptions({
    id,
    entityType,
    enabled,
  });
  return useQuery(options);
};

// Create a unified hook that chooses between admin and proponent endpoints
export const useGetActivityLog = ({
  id,
  entityType,
  isAdmin = false,
  enabled = undefined,
}: UseGetActivityLogForAdminByIdParams & { isAdmin?: boolean }) => {
  // Always call both hooks
  const adminResult = useGetActivityLogForAdmin({
    id,
    entityType,
    enabled: enabled && isAdmin,
  });

  const proponentResult = useGetActivityLogForProponent({
    id,
    entityType,
    enabled: enabled && !isAdmin,
  });

  // Return the appropriate result based on isAdmin
  return isAdmin ? adminResult : proponentResult;
};
