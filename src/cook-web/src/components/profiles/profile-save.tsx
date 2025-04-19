/** inject profile to mc-editor */
'use client'
import React, { useState, useEffect } from 'react'
import { X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import type { Profile, EnumItem, DataType } from '@/components/profiles/type'
import api from '@/api'
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem
} from '@/components/ui/select'

interface ProfileSaveProps {
  parentId?: string
  value?: Profile
  open?: boolean
  onOpenChange?: (open: boolean) => void
  onSaveSuccess?: (profile: Profile) => void
}

const ProfileSave: React.FC<ProfileSaveProps> = ({
  parentId,
  value,
  open,
  onOpenChange,
  onSaveSuccess = () => {}
}) => {
  const [isEditing, setIsEditing] = useState(!!value?.id)
  const [editingId, setEditingId] = useState<number>()
  const [profile, setProfile] = useState<Profile>({
    name: '',
    title: '',
    type: 'custom',
    dataType: 'string',
    defaultValue: '',
    enumItems: []
  })
  const [newEnumItem, setNewEnumItem] = useState<EnumItem>({
    value: '',
    title: ''
  })

  const resetForm = () => {
    setProfile({
      name: '',
      title: '',
      type: 'custom',
      dataType: 'string',
      defaultValue: '',
      enumItems: []
    })
    setNewEnumItem({ value: '', title: '' })
    setIsEditing(false)
    setEditingId(undefined)
  }

  const handleSaveProfile = async () => {
    if (profile.name.trim()) {
      const profileToSave: Profile = {
        ...profile,
        enumItems: profile.dataType === 'enum' ? profile.enumItems : undefined,
        defaultValue:
          profile.dataType === 'string' ? profile.defaultValue : undefined,
        id: editingId
      }
      // TODO: test code
      const res =
        true ||
        (await api.saveProfile({
          parentId,
          data: profileToSave
        }))
      if (res) {
        onSaveSuccess?.(profileToSave)
        resetForm()
        // setDialogOpen(false)
        onOpenChange?.(false)
      }
    }
  }

  const handleAddEnumItem = () => {
    if (newEnumItem.value.trim() && newEnumItem.title.trim()) {
      setProfile({
        ...profile,
        enumItems: [...(profile.enumItems || []), { ...newEnumItem }]
      })
      setNewEnumItem({ value: '', title: '' })
    }
  }

  const handleRemoveEnumItem = (index: number) => {
    const updatedEnumItems = [...(profile.enumItems || [])]
    updatedEnumItems.splice(index, 1)
    setProfile({
      ...profile,
      enumItems: updatedEnumItems
    })
  }

  useEffect(() => {
    if (value) {
      setProfile(value)
      setEditingId(value.id as unknown as number)
      setIsEditing(!!value.id)
    } else {
      resetForm()
    }
  }, [value])

  return (
    <>
      <Dialog
        open={open}
        onOpenChange={() => {
          resetForm()
          onOpenChange?.(!open)
        }}
      >
        <DialogContent className='sm:max-w-[500px]'>
          <DialogHeader>
            <DialogTitle>{isEditing ? '编辑变量' : '添加新变量'}</DialogTitle>
            <DialogDescription>
              {isEditing ? '修改现有变量的属性。' : '创建一个新的自定义变量。'}
            </DialogDescription>
          </DialogHeader>
          <div className='grid gap-4 py-4'>
            <div className='grid grid-cols-4 items-center gap-4'>
              <Label htmlFor='name' className='text-right'>
                变量名
              </Label>
              <Input
                id='name'
                value={profile.name}
                onChange={e => setProfile({ ...profile, name: e.target.value })}
                className='col-span-3'
              />
            </div>
            <div className='grid grid-cols-4 items-center gap-4'>
              <Label htmlFor='title' className='text-right'>
                标题
              </Label>
              <Input
                id='title'
                value={profile.title}
                onChange={e =>
                  setProfile({ ...profile, title: e.target.value })
                }
                className='col-span-3'
                placeholder='可选'
              />
            </div>
            <div className='grid grid-cols-4 items-center gap-4'>
              <Label className='text-right'>数据类型</Label>
              <div className='col-span-3'>
                <RadioGroup
                  value={profile.dataType}
                  onValueChange={(value: DataType) =>
                    setProfile({ ...profile, dataType: value })
                  }
                  className='flex flex-row space-x-4'
                >
                  <div className='flex items-center space-x-2'>
                    <RadioGroupItem value='string' id='string' />
                    <Label htmlFor='string'>字符串</Label>
                  </div>
                  <div className='flex items-center space-x-2'>
                    <RadioGroupItem value='enum' id='enum' />
                    <Label htmlFor='enum'>枚举</Label>
                  </div>
                </RadioGroup>
              </div>
            </div>

            {profile.dataType === 'string' && (
              <div className='grid grid-cols-4 items-center gap-4'>
                <Label htmlFor='defaultValue' className='text-right'>
                  默认值
                </Label>
                <Input
                  id='defaultValue'
                  value={profile.defaultValue || ''}
                  onChange={e =>
                    setProfile({
                      ...profile,
                      defaultValue: e.target.value
                    })
                  }
                  className='col-span-3'
                  placeholder='可选'
                />
              </div>
            )}

            {profile.dataType === 'enum' && (
              <>
                <div className='grid grid-cols-4 gap-4'>
                  <div className='col-span-4'>
                    <Label className='mb-2 block'>枚举项</Label>
                    {!!profile.enumItems?.length && (
                      <div className='mb-3 rounded-md border'>
                        <div className='grid grid-cols-12 border-b bg-muted px-3 py-2 text-sm font-medium'>
                          <div className='col-span-5'>枚举值</div>
                          <div className='col-span-5'>标题</div>
                          <div className='col-span-2 text-right'>操作</div>
                        </div>
                        <div className='divide-y'>
                          {(profile.enumItems || []).map((item, index) => (
                            <div
                              key={index}
                              className='grid grid-cols-12 items-center px-3 py-2'
                            >
                              <div className='col-span-5 truncate'>
                                {item.value}
                              </div>
                              <div className='col-span-5 truncate'>
                                {item.title}
                              </div>
                              <div className='col-span-2 text-right'>
                                <Button
                                  variant='ghost'
                                  size='icon'
                                  className='h-7 w-7'
                                  onClick={() => handleRemoveEnumItem(index)}
                                >
                                  <X className='h-4 w-4' />
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className='grid grid-cols-12 gap-2'>
                      <Input
                        placeholder='枚举值'
                        value={newEnumItem.value}
                        onChange={e =>
                          setNewEnumItem({
                            ...newEnumItem,
                            value: e.target.value
                          })
                        }
                        className='col-span-5'
                      />
                      <Input
                        placeholder='标题'
                        value={newEnumItem.title}
                        onChange={e =>
                          setNewEnumItem({
                            ...newEnumItem,
                            title: e.target.value
                          })
                        }
                        className='col-span-5'
                      />
                      <Button
                        onClick={handleAddEnumItem}
                        className='col-span-2 h-8'
                        disabled={
                          !newEnumItem.value.trim() || !newEnumItem.title.trim()
                        }
                      >
                        添加
                      </Button>
                    </div>
                  </div>
                </div>
                {!!profile.enumItems?.length && (
                  <div className='grid grid-cols-4 gap-4'>
                    <div className='col-span-4 flex flex-row justify-between align-items-center'>
                      <Label className='block w-30' htmlFor='defaultValue'>
                        默认值
                      </Label>
                      <Select
                        onValueChange={(value: string) => {
                          setProfile({
                            ...profile,
                            defaultValue: value || ''
                          })
                        }}
                        defaultValue={profile.defaultValue}
                      >
                        <SelectTrigger className='rounded-md border'>
                          <SelectValue placeholder='可选' />
                        </SelectTrigger>
                        <SelectContent className='rounded-md border'>
                          {(profile.enumItems || []).map(item => (
                            <SelectItem
                              key={item.value}
                              value={item.value}
                              className='cursor-pointer'
                            >
                              {item.title}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
          <DialogFooter>
            <Button
              className='h-8'
              variant='outline'
              onClick={() => {
                resetForm()
                onOpenChange?.(!open)
              }}
            >
              取消
            </Button>
            <Button
              className='h-8'
              onClick={handleSaveProfile}
              disabled={
                !profile.name.trim() ||
                (profile.dataType === 'enum' &&
                  (profile.enumItems || []).length === 0)
              }
            >
              {isEditing ? '保存' : '添加'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
export default ProfileSave
