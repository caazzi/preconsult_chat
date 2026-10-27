import {Box as RadixThemesBox,Flex as RadixThemesFlex,Heading as RadixThemesHeading,Separator as RadixThemesSeparator,Table as RadixThemesTable,Text as RadixThemesText} from "@radix-ui/themes"
import {Button_button_017d529b4de1fc08cad251e0f5d94ce4_fb35b5b8,Button_button_e9634e9129c5fef32f633aa2241a15aa_fb35b5b8,Center_flex_08e3cc371f521fc6f933ce7e6b3bbfe9_fb35b5b8,Cond_comp_202fae3e2d8d9ea4791e8b4294ae523b_fb35b5b8,Foreach_comp_5ce5fab84cf37f6a7970463016d1da0e_fb35b5b8} from "$/app_components/preconsult/preconsult"
import {Fragment,useEffect} from "react"
import {Lock as LucideLock} from "lucide-react"
import {jsx} from "@emotion/react"





export default function Component() {





  return (
    jsx(Fragment,{},jsx(Center_flex_08e3cc371f521fc6f933ce7e6b3bbfe9_fb35b5b8,{},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["maxWidth"] : "1000px", ["width"] : "90%", ["alignItems"] : "center", ["paddingTop"] : "5em", ["paddingBottom"] : "5em" }),direction:"column",gap:"3"},jsx(Fragment,{},jsx(Cond_comp_202fae3e2d8d9ea4791e8b4294ae523b_fb35b5b8,{},jsx(Fragment,{},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%", ["padding"] : "2em", ["background"] : "rgba(255,255,255,0.05)", ["backdropFilter"] : "blur(15px)", ["border"] : "1px solid rgba(255,255,255,0.1)", ["borderRadius"] : "20px" }),direction:"column",gap:"6"},jsx(RadixThemesHeading,{color:"cyan",size:"8"},"Admin Analytics Dashboard \ud83d\udcca"),jsx(RadixThemesText,{as:"p",color:"gray"},"Conversion Funnel Metrics (Last 7 Days)"),jsx(RadixThemesSeparator,{size:"4"},),jsx(RadixThemesBox,{css:({ ["overflowX"] : "auto", ["width"] : "100%" })},jsx(RadixThemesTable.Root,{css:({ ["width"] : "100%" }),variant:"ghost"},jsx(RadixThemesTable.Header,{},jsx(RadixThemesTable.Row,{},jsx(RadixThemesTable.ColumnHeaderCell,{},"Date"),jsx(RadixThemesTable.ColumnHeaderCell,{},"Demographics"),jsx(RadixThemesTable.ColumnHeaderCell,{},"Complaint"),jsx(RadixThemesTable.ColumnHeaderCell,{},"History"),jsx(RadixThemesTable.ColumnHeaderCell,{},"Lifestyle"),jsx(RadixThemesTable.ColumnHeaderCell,{},"Summary"),jsx(RadixThemesTable.ColumnHeaderCell,{},"PDF Download"))),jsx(RadixThemesTable.Body,{},jsx(Foreach_comp_5ce5fab84cf37f6a7970463016d1da0e_fb35b5b8,{},)))),jsx(Button_button_017d529b4de1fc08cad251e0f5d94ce4_fb35b5b8,{},"Back to Home"))),jsx(Fragment,{},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["padding"] : "2em", ["alignItems"] : "center", ["border"] : "1px solid rgba(255,255,255,0.1)", ["borderRadius"] : "20px" }),direction:"column",gap:"4"},jsx(LucideLock,{css:({ ["color"] : "red" }),size:48},),jsx(RadixThemesHeading,{css:({ ["color"] : "red" }),size:"6"},"Unauthorized"),jsx(RadixThemesText,{as:"p",color:"gray",css:({ ["textAlign"] : "center" })},"Please provide a valid token in the URL query parameters (e.g. ?token=...)."),jsx(Button_button_e9634e9129c5fef32f633aa2241a15aa_fb35b5b8,{},"Back to Home"))))))),jsx("title",{},"PreConsult Admin Dashboard"),jsx("meta",{content:"Analytics funnel dashboard for PreConsult administrators.",name:"description"},),jsx("meta",{content:"favicon.ico",property:"og:image"},))
  )
}