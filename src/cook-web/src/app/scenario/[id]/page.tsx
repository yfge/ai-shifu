import Header from '@/components/header'
import ScenarioEdit from '@/components/scenario-edit'
export default async function Page({
    params,
}: {
    params: Promise<{ id: string }>
}) {
    const id = (await params).id;
    console.log(id)
    return (
        <div className='h-screen w-full'>
            <div className='sticky top-0'>
                <Header />
            </div>
            <ScenarioEdit id={id} />
        </div>
    )
}

