import { useMutation, useQuery } from "@tanstack/react-query";
import { submitRequest } from "@/utils/axiosUtils";
import { QUERY_KEY } from "./constants";
import { StaffUser } from "@/models/User";

type CreateStaffRequest = {
  first_name?: string;
  last_name?: string;
  work_email_address?: string;
  auth_guid?: string;
};

const fetchStaffUserByGUID = (id?: string) => {
  return submitRequest<StaffUser>({ url: `staff-user/${id}` });
};

const addStaffUser = (data: CreateStaffRequest) => {
  return submitRequest<StaffUser>({
    url: "staff-user",
    method: "post",
    data,
  });
};

export const useStaffUserById = (userId?: string) => {
  return useQuery({
    queryKey: [QUERY_KEY.STAFF_USER, userId],
    queryFn: () => fetchStaffUserByGUID(userId),
    enabled: !!userId,
  });
};

export const useStaffAddUser = () => {
  return useMutation({
    mutationFn: addStaffUser,
  });
};
