import CourseSection from "./CourseSection.jsx";

export const CourseCatalog = ({ chapterList = [{id: 0}] }) => {
  return (<div>
    <div>
      <div>第一章</div>
      <div>
        <div></div>
        <div></div>
        <div></div>
      </div>
    </div>

    {
      chapterList.map(e => {
        return (<CourseSection key={e.id} {...e} />)
      })
    }

  </div>)
}

export default CourseCatalog;
