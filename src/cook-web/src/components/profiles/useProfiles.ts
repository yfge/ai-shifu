import { useState, useEffect } from 'react'
import type { Profile } from './type'
import api from '@/api'

type useProfileParams = {
  parentId?: number
  searchTerm: string
  refreshFlag?: number
}
const useProfiles = ({
  parentId,
  searchTerm,
  refreshFlag
}: useProfileParams) => {
  const [profiles, setProfiles] = useState<Profile[]>()
  const fetchList = async () => {
    // TODO: test data
    const testProfiles = [
      {
        id: '1',
        name: '用户名',
        title: '当前登录用户的名称',
        type: 'system',
        dataType: 'string'
      },
      {
        id: '2',
        name: '邮箱',
        title: '用户邮箱地址',
        type: 'system',
        dataType: 'string'
      },
      {
        id: '3',
        name: '手机号',
        title: '用户手机号码',
        type: 'system',
        dataType: 'string'
      },
      {
        id: '4',
        name: '状态',
        title: '用户状态',
        type: 'custom',
        dataType: 'enum',
        enumItems: [
          { value: 'active', title: '活跃' },
          { value: 'inactive', title: '非活跃' }
        ]
      }
    ]
    const list =
      testProfiles ||
      api.getProfileList({
        parentId
      })
    setProfiles(list as unknown as Profile[])
  }

  const getProfilesByType = (profiles: Profile[] | undefined) => {
    const filteredProfiles = profiles?.filter(
      profile =>
        profile.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        profile.title.toLowerCase().includes(searchTerm.toLowerCase())
    )
    const systemProfiles = filteredProfiles?.filter(v => v.type === 'system')
    const customProfiles = filteredProfiles?.filter(v => v.type === 'custom')
    return [systemProfiles, customProfiles]
  }

  useEffect(() => {
    fetchList()
  }, [parentId, refreshFlag])

  return getProfilesByType(profiles)
}

export default useProfiles
