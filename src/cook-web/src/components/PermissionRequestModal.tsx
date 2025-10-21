import { useCallback, memo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/Dialog';

import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from '@/components/ui/Form';

import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';

import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

import { submitFeedback } from '@/c-api/bz';
import { toast } from '@/hooks/useToast';

const REQUEST_MAX_LENGTH = 300;

interface PermissionRequestModalProps {
  open: boolean;
  onClose: () => void;
}

export const PermissionRequestModal = ({
  open,
  onClose,
}: PermissionRequestModalProps) => {
  const { t } = useTranslation('translation', { keyPrefix: 'c' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const formSchema = z.object({
    request: z.string().min(5, {
      message: t('module.permission.permission.requestPlaceholder'),
    }),
  });

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      request: '',
    },
  });

  const onSubmitRequest = useCallback(
    async (values: z.infer<typeof formSchema>) => {
      if (isSubmitting) return;

      setIsSubmitting(true);
      try {
        const { request } = values;
        // Trim the input before processing
        const trimmedRequest = request.trim();
        const requestContent = `[权限申请] ${trimmedRequest}`;

        await submitFeedback(requestContent);

        toast({
          title: t('module.permission.permission.requestSuccess'),
        });
        form.reset();
        onClose();
      } catch (error) {
        console.error('Permission request submission failed:', error);
        toast({
          title: t('module.permission.permission.requestError'),
          variant: 'destructive',
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [onClose, t, form, isSubmitting],
  );

  function handleOpenChange(open: boolean) {
    if (!open) {
      form.reset();
      onClose();
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={handleOpenChange}
    >
      <DialogContent className='sm:max-w-md'>
        <DialogHeader>
          <DialogTitle className='text-center text-lg'>
            {t('module.permission.permission.requestTitle')}
          </DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmitRequest)}>
            <div className='py-4'>
              <p className='text-sm text-gray-600 mb-4'>
                {t('module.permission.permission.requestDescription')}
              </p>

              <FormField
                control={form.control}
                name='request'
                render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Textarea
                        maxLength={REQUEST_MAX_LENGTH}
                        minLength={5}
                        placeholder={t(
                          'module.permission.permission.requestPlaceholder',
                        )}
                        className='resize-none h-24'
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <DialogFooter className='flex justify-between items-center'>
              <Button
                type='button'
                variant='outline'
                onClick={() => handleOpenChange(false)}
                className='min-w-[100px]'
              >
                {t('common.core.cancel')}
              </Button>
              <Button
                type='submit'
                disabled={isSubmitting}
                className='min-w-[120px]'
              >
                {isSubmitting
                  ? t('common.core.submitting')
                  : t('module.permission.permission.requestSubmit')}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
};

export default memo(PermissionRequestModal);
