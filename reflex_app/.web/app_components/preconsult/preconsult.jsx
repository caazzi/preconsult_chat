
import {ReflexEvent,applyEventActions,isNotNullOrUndefined,isTrue,pyAnd,pyOr} from "$/utils/state"
import {ColorModeContext,StateContexts,addEvents} from "$/utils/context"
import {Fragment,memo,useCallback,useContext,useEffect} from "react"
import {jsx} from "@emotion/react"
import {Box as RadixThemesBox,Button as RadixThemesButton,Card as RadixThemesCard,Flex as RadixThemesFlex,IconButton as RadixThemesIconButton,Link as RadixThemesLink,Progress as RadixThemesProgress,SegmentedControl as RadixThemesSegmentedControl,Select as RadixThemesSelect,Table as RadixThemesTable,Text as RadixThemesText,TextArea as RadixThemesTextArea,TextField as RadixThemesTextField} from "@radix-ui/themes"
import DebounceInput from "react-debounce-input"
import {ChevronDown as LucideChevronDown,Trash as LucideTrash} from "lucide-react"
import {Trigger as RadixAccordionTrigger} from "@radix-ui/react-accordion"
import {Link as ReactRouterLink} from "react-router"








export const Bare_comp_dcd27e2cda435d4ad3d41a588d187d3c_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["title"]
    )
});

export const Bare_comp_c1d6cd9b04652ac14503d99194aeed26_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["lang_select_sr"]
    )
});

export const Selectroot_select__root_2d37aee753ce629623873382d86c5a45_fb35b5b8 = memo(({children}) => {
    const on_change_2f5dca765e6516f1b2985cfdad4eae98 = useCallback(((_ev_0) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_lang", ({ ["val"] : _ev_0 }), ({  })))], [_ev_0], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesSelect.Root,{"aria-label":"Select language",css:({ ["minHeight"] : "44px" }),onValueChange:on_change_2f5dca765e6516f1b2985cfdad4eae98,value:reflex___state____state__preconsult___state____state.lang_rx_state_},children)
    )
});

export const Cond_comp_349cac9629d9e06fa39ce75af0d828d5_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 0?.valueOf?.())?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Cond_comp_527d63a56bc1b3c4f56b5c5d9398cf35_fb35b5b8 = memo(({children}) => {
    const { resolvedColorMode } = useContext(ColorModeContext)



    return(
        ((resolvedColorMode?.valueOf?.() === "light"?.valueOf?.())?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Iconbutton_iconbutton_a65bfc6c7291cd642367c97b948c5cf8_fb35b5b8 = memo(({children}) => {
    const { toggleColorMode } = useContext(ColorModeContext)
const on_click_dedd885ce47a15c1666b026c014cf563 = useCallback(((_e) => (toggleColorMode(_e))), [addEvents, ReflexEvent, toggleColorMode])



    return(
        jsx(RadixThemesIconButton,{"aria-label":"Toggle color mode",css:({ ["padding"] : "6px", ["background"] : "transparent", ["color"] : "inherit", ["zIndex"] : "20", ["&:hover"] : ({ ["cursor"] : "pointer" }) }),onClick:on_click_dedd885ce47a15c1666b026c014cf563},children)
    )
});

export const Hstack_flex_c6a0066658f5170965ff929f13ce3d1d_fb35b5b8 = memo(({children}) => {
    const { rawColorMode } = useContext(ColorModeContext)



    return(
        jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%", ["padding"] : ({ ["initial"] : "0.5em 1em", ["sm"] : "1em" }), ["borderBottom"] : ((rawColorMode?.valueOf?.() === "light"?.valueOf?.()) ? "1px solid rgba(0, 0, 0, 0.08)" : "1px solid rgba(255, 255, 255, 0.1)") }),direction:"row",gap:"3"},children)
    )
});

export const Bare_comp_ab550bcba7d05a11243eb198201eeddd_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_indicator"]
    )
});

export const Bare_comp_ed83fe133e6d196a1afc7d64b3bd7be8_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.active_step_number_rx_state_
    )
});

export const Bare_comp_20eeddb70e9b2393cee21082c03db25b_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["of_indicator"]
    )
});

export const Bare_comp_36334249f67a796cbe4c7d8a9f0ba0d8_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.total_active_steps_rx_state_
    )
});

export const Bare_comp_476e50c35f88332730acc302729d36ad_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.active_step_name_rx_state_
    )
});

export const Cond_comp_4489fcf9769c6e53a03f0b1577267a85_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        (!((reflex___state____state__preconsult___state____state.active_step_name_rx_state_?.valueOf?.() === ""?.valueOf?.()))?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Progress_progress_2543472c9c17404f3f3398f41826b2a3_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesProgress,{"aria-label":"Overall intake progress",color:"cyan",css:({ ["width"] : "100%", ["height"] : "6px", ["borderRadius"] : "999px" }),value:reflex___state____state__preconsult___state____state.step_progress_rx_state_},)
    )
});

export const Cond_comp_5ecc3351f0039dd041de19ce9c79bc5a_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 0), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.())))?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Box_box_e228da4390aceb13186927616262c0da_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesBox,{css:({ ["aspectRatio"] : "1 / 1", ["flexShrink"] : 0, ["display"] : "flex", ["alignItems"] : "center", ["justifyContent"] : "center", ["width"] : "32px", ["height"] : "32px", ["minWidth"] : "32px", ["minHeight"] : "32px", ["borderRadius"] : "50%", ["background"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 0?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "rgba(0, 242, 254, 0.25)" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 0), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "rgba(0, 242, 254, 0.4)" : "rgba(255,255,255,0.03)")), ["border"] : "2px solid", ["borderColor"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 0?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "#00f2fe" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 0), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "#00c8ff" : "rgba(255,255,255,0.18)")), ["boxShadow"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 0?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "0 0 12px rgba(0, 242, 254, 0.4)" : "none"), ["color"] : (pyOr(pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 0?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))), () => (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 0), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))))) ? "#00f2fe" : "rgba(255,255,255,0.5)"), ["transition"] : "all 0.2s ease-in-out" })},children)
    )
});

export const Bare_comp_9d2866e69cdd14eafabc7aa4ea6647d2_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.step_names_rx_state_?.at?.(0)
    )
});

export const Text_text_be51ba1c7ab7063edae2ad5b0ab22ce9_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesText,{as:"p",css:({ ["color"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 0?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "white" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 0), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "#e2e8f0" : "rgba(255,255,255,0.4)")), ["whiteSpace"] : "nowrap" }),size:"2",weight:(pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 0?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "bold" : "regular")},children)
    )
});

export const Cond_comp_e14d394d695492713143a4b39ffb1c53_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        ((reflex___state____state__preconsult___state____state.step_names_rx_state_.length > 0)?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Box_box_70deea417545de92f9640b229cdec04c_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesBox,{css:({ ["flex"] : "1", ["height"] : "2px", ["minWidth"] : "12px", ["background"] : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 0), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "linear-gradient(90deg, #00c8ff, #00f2fe)" : "rgba(255, 255, 255, 0.12)"), ["marginInlineStart"] : "4px", ["marginInlineEnd"] : "4px", ["transition"] : "all 0.3s ease" })},)
    )
});

export const Cond_comp_54ab4e867651db72dd7852905e72bf8b_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 1), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.())))?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Box_box_1418655e6418e6da67d987b9a9cd830f_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesBox,{css:({ ["aspectRatio"] : "1 / 1", ["flexShrink"] : 0, ["display"] : "flex", ["alignItems"] : "center", ["justifyContent"] : "center", ["width"] : "32px", ["height"] : "32px", ["minWidth"] : "32px", ["minHeight"] : "32px", ["borderRadius"] : "50%", ["background"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 1?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "rgba(0, 242, 254, 0.25)" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 1), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "rgba(0, 242, 254, 0.4)" : "rgba(255,255,255,0.03)")), ["border"] : "2px solid", ["borderColor"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 1?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "#00f2fe" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 1), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "#00c8ff" : "rgba(255,255,255,0.18)")), ["boxShadow"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 1?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "0 0 12px rgba(0, 242, 254, 0.4)" : "none"), ["color"] : (pyOr(pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 1?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))), () => (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 1), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))))) ? "#00f2fe" : "rgba(255,255,255,0.5)"), ["transition"] : "all 0.2s ease-in-out" })},children)
    )
});

export const Bare_comp_3b19b5d0b7aa2e7ad8863df6b98bb82b_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.step_names_rx_state_?.at?.(1)
    )
});

export const Text_text_12e962371438b35a4f6e2c6e4219e4a8_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesText,{as:"p",css:({ ["color"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 1?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "white" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 1), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "#e2e8f0" : "rgba(255,255,255,0.4)")), ["whiteSpace"] : "nowrap" }),size:"2",weight:(pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 1?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "bold" : "regular")},children)
    )
});

export const Cond_comp_1c90ac8d554a98a0f5f2967ed290a3ec_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        ((reflex___state____state__preconsult___state____state.step_names_rx_state_.length > 1)?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Box_box_cc36771186725ee0a56953de5d526182_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesBox,{css:({ ["flex"] : "1", ["height"] : "2px", ["minWidth"] : "12px", ["background"] : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 1), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "linear-gradient(90deg, #00c8ff, #00f2fe)" : "rgba(255, 255, 255, 0.12)"), ["marginInlineStart"] : "4px", ["marginInlineEnd"] : "4px", ["transition"] : "all 0.3s ease" })},)
    )
});

export const Cond_comp_559fc610fd118858782dcc175cfe2cf5_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 2), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.())))?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Box_box_e88e241a7771e6518caf72eaacf600c7_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesBox,{css:({ ["aspectRatio"] : "1 / 1", ["flexShrink"] : 0, ["display"] : "flex", ["alignItems"] : "center", ["justifyContent"] : "center", ["width"] : "32px", ["height"] : "32px", ["minWidth"] : "32px", ["minHeight"] : "32px", ["borderRadius"] : "50%", ["background"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 2?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "rgba(0, 242, 254, 0.25)" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 2), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "rgba(0, 242, 254, 0.4)" : "rgba(255,255,255,0.03)")), ["border"] : "2px solid", ["borderColor"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 2?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "#00f2fe" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 2), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "#00c8ff" : "rgba(255,255,255,0.18)")), ["boxShadow"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 2?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "0 0 12px rgba(0, 242, 254, 0.4)" : "none"), ["color"] : (pyOr(pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 2?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))), () => (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 2), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))))) ? "#00f2fe" : "rgba(255,255,255,0.5)"), ["transition"] : "all 0.2s ease-in-out" })},children)
    )
});

export const Bare_comp_f398cbce339f7044e015d53c59a6c6b4_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.step_names_rx_state_?.at?.(2)
    )
});

export const Text_text_a3aa2983491e5ea1bd885daafe4784a4_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesText,{as:"p",css:({ ["color"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 2?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "white" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 2), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "#e2e8f0" : "rgba(255,255,255,0.4)")), ["whiteSpace"] : "nowrap" }),size:"2",weight:(pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 2?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "bold" : "regular")},children)
    )
});

export const Cond_comp_6ed08402a93dec0b1d5ccb7925921b80_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        ((reflex___state____state__preconsult___state____state.step_names_rx_state_.length > 2)?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Box_box_445883c8ca7ae657cb354d4f3df7ba02_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesBox,{css:({ ["flex"] : "1", ["height"] : "2px", ["minWidth"] : "12px", ["background"] : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 2), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "linear-gradient(90deg, #00c8ff, #00f2fe)" : "rgba(255, 255, 255, 0.12)"), ["marginInlineStart"] : "4px", ["marginInlineEnd"] : "4px", ["transition"] : "all 0.3s ease" })},)
    )
});

export const Cond_comp_bab4de89822ed41820706f39a05dd190_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 3), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.())))?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Box_box_9b4f157198ca047a033b459cc6114079_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesBox,{css:({ ["aspectRatio"] : "1 / 1", ["flexShrink"] : 0, ["display"] : "flex", ["alignItems"] : "center", ["justifyContent"] : "center", ["width"] : "32px", ["height"] : "32px", ["minWidth"] : "32px", ["minHeight"] : "32px", ["borderRadius"] : "50%", ["background"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 3?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "rgba(0, 242, 254, 0.25)" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 3), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "rgba(0, 242, 254, 0.4)" : "rgba(255,255,255,0.03)")), ["border"] : "2px solid", ["borderColor"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 3?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "#00f2fe" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 3), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "#00c8ff" : "rgba(255,255,255,0.18)")), ["boxShadow"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 3?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "0 0 12px rgba(0, 242, 254, 0.4)" : "none"), ["color"] : (pyOr(pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 3?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))), () => (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 3), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))))) ? "#00f2fe" : "rgba(255,255,255,0.5)"), ["transition"] : "all 0.2s ease-in-out" })},children)
    )
});

export const Bare_comp_a18ba557162318e789192111faef4535_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.step_names_rx_state_?.at?.(3)
    )
});

export const Text_text_be52e3cb4d738ec3cad93125ea0c78fc_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesText,{as:"p",css:({ ["color"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 3?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "white" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 3), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "#e2e8f0" : "rgba(255,255,255,0.4)")), ["whiteSpace"] : "nowrap" }),size:"2",weight:(pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 3?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "bold" : "regular")},children)
    )
});

export const Cond_comp_60b112f6009fd615558f1713c6848cde_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        ((reflex___state____state__preconsult___state____state.step_names_rx_state_.length > 3)?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Box_box_c5e24c96b33c0cb2114b5d14f94b9421_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesBox,{css:({ ["flex"] : "1", ["height"] : "2px", ["minWidth"] : "12px", ["background"] : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 3), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "linear-gradient(90deg, #00c8ff, #00f2fe)" : "rgba(255, 255, 255, 0.12)"), ["marginInlineStart"] : "4px", ["marginInlineEnd"] : "4px", ["transition"] : "all 0.3s ease" })},)
    )
});

export const Cond_comp_f9dbbfc5c7457642c304caa937111b62_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 4), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.())))?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Box_box_2e32acfd51c1eec2e39351046a181312_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesBox,{css:({ ["aspectRatio"] : "1 / 1", ["flexShrink"] : 0, ["display"] : "flex", ["alignItems"] : "center", ["justifyContent"] : "center", ["width"] : "32px", ["height"] : "32px", ["minWidth"] : "32px", ["minHeight"] : "32px", ["borderRadius"] : "50%", ["background"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 4?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "rgba(0, 242, 254, 0.25)" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 4), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "rgba(0, 242, 254, 0.4)" : "rgba(255,255,255,0.03)")), ["border"] : "2px solid", ["borderColor"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 4?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "#00f2fe" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 4), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "#00c8ff" : "rgba(255,255,255,0.18)")), ["boxShadow"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 4?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "0 0 12px rgba(0, 242, 254, 0.4)" : "none"), ["color"] : (pyOr(pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 4?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))), () => (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 4), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))))) ? "#00f2fe" : "rgba(255,255,255,0.5)"), ["transition"] : "all 0.2s ease-in-out" })},children)
    )
});

export const Bare_comp_62d24dc7d00ae031956f7df7a173908b_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.step_names_rx_state_?.at?.(4)
    )
});

export const Text_text_f2d10f1105ca3b2851f8a7bff4523021_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesText,{as:"p",css:({ ["color"] : (pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 4?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "white" : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 4), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "#e2e8f0" : "rgba(255,255,255,0.4)")), ["whiteSpace"] : "nowrap" }),size:"2",weight:(pyAnd((reflex___state____state__preconsult___state____state.active_step_index_rx_state_?.valueOf?.() === 4?.valueOf?.()), () => ((reflex___state____state__preconsult___state____state.step_rx_state_ < 6))) ? "bold" : "regular")},children)
    )
});

export const Cond_comp_84d0803a22578d28df52c61081065ab7_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        ((reflex___state____state__preconsult___state____state.step_names_rx_state_.length > 4)?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Box_box_9e5f98f4eb30567f1a4765d4166671ff_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesBox,{css:({ ["flex"] : "1", ["height"] : "2px", ["minWidth"] : "12px", ["background"] : (pyOr((reflex___state____state__preconsult___state____state.active_step_index_rx_state_ > 4), () => ((reflex___state____state__preconsult___state____state.step_rx_state_?.valueOf?.() === 6?.valueOf?.()))) ? "linear-gradient(90deg, #00c8ff, #00f2fe)" : "rgba(255, 255, 255, 0.12)"), ["marginInlineStart"] : "4px", ["marginInlineEnd"] : "4px", ["transition"] : "all 0.3s ease" })},)
    )
});

export const Cond_comp_bc6b169cc1cd9fb6efc8d81e76af18a5_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        ((reflex___state____state__preconsult___state____state.step_rx_state_ > 0)?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Bare_comp_2ffeea803224e5abbcaf25e5c9255953_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["privacy_badge_landing"]
    )
});

export const Bare_comp_ae6458ffe9419e1ce44cb7ccc7e041ce_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["hero_title"]
    )
});

export const Bare_comp_cd108167b422a4eacfe9be0702e1c9ea_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["hero_subtitle"]
    )
});

export const Bare_comp_2912d2898539cdebe98971f4caddca09_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_how_1"]
    )
});

export const Bare_comp_571dc78ebc148fd60095c3dab47097dc_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_sub_1"]
    )
});

export const Bare_comp_cfa4d120b7fe0647cb015090665ffa44_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_how_2"]
    )
});

export const Bare_comp_332dd7853e50fc6a0dd2c70cb987be5f_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_sub_2"]
    )
});

export const Bare_comp_09c72aabd5760c29a09ca55be2bcaf39_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_how_3"]
    )
});

export const Bare_comp_83e9e5e2315598bd9728e055962152ea_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_sub_3"]
    )
});

export const Bare_comp_7d69091155c0bfdc51caee1fe09cefa1_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["start_cta"]
    )
});

export const Button_button_b1022b1967c16c527667f114f3e9a5bd_fb35b5b8 = memo(({children}) => {
    const on_click_2b4e27819623afa627cdc97eaadce54d = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.start_intake", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])



    return(
        jsx(RadixThemesButton,{color:"cyan",css:({ ["width"] : "100%", ["minHeight"] : "48px", ["&:hover"] : ({ ["transform"] : "scale(1.02)", ["background"] : "cyan.600" }), ["transition"] : "all 0.2s ease", ["animation"] : "fadeInUp 0.4s ease-out 0.2s both" }),onClick:on_click_2b4e27819623afa627cdc97eaadce54d,size:"4"},children)
    )
});

export const Bare_comp_2b53a71865ed5a88c6712799a0582753_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.error_message_rx_state_
    )
});

export const Cond_comp_c2ce07118c2ec3dc92efe553b73f2232_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        (!((reflex___state____state__preconsult___state____state.error_message_rx_state_?.valueOf?.() === ""?.valueOf?.()))?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Bare_comp_57ce807e204dc430968fd9d31380655b_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["intake"]
    )
});

export const Bare_comp_10bb0b972d51c75d4f827b6f07e39c41_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["intake_desc"]
    )
});

export const Bare_comp_b4eeee49256072ecb38d8b82f70e84ca_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["age"]
    )
});

export const Button_button_abd917da3d46b7fa14c9ab3ffc6922d6_fb35b5b8 = memo(({children}) => {
    const on_click_795dc9ac56819b0d5035210b3cc51f44 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_age_bracket", ({ ["val"] : "18-25" }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesButton,{css:({ ["width"] : "100%", ["minHeight"] : "48px" }),onClick:on_click_795dc9ac56819b0d5035210b3cc51f44,variant:((reflex___state____state__preconsult___state____state.age_bracket_rx_state_?.valueOf?.() === "18-25"?.valueOf?.()) ? "solid" : "outline")},children)
    )
});

export const Button_button_c35f13b21a0484d5af2ad79675bfecb3_fb35b5b8 = memo(({children}) => {
    const on_click_c3f8c802e440ecbf27c832ea85abe433 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_age_bracket", ({ ["val"] : "26-35" }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesButton,{css:({ ["width"] : "100%", ["minHeight"] : "48px" }),onClick:on_click_c3f8c802e440ecbf27c832ea85abe433,variant:((reflex___state____state__preconsult___state____state.age_bracket_rx_state_?.valueOf?.() === "26-35"?.valueOf?.()) ? "solid" : "outline")},children)
    )
});

export const Button_button_cdc4329f29eeb23c31be878fbc31f084_fb35b5b8 = memo(({children}) => {
    const on_click_51c07675ad27feedab6d6d0d54c5f70d = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_age_bracket", ({ ["val"] : "36-45" }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesButton,{css:({ ["width"] : "100%", ["minHeight"] : "48px" }),onClick:on_click_51c07675ad27feedab6d6d0d54c5f70d,variant:((reflex___state____state__preconsult___state____state.age_bracket_rx_state_?.valueOf?.() === "36-45"?.valueOf?.()) ? "solid" : "outline")},children)
    )
});

export const Button_button_1d0cb269cfd249fe7f50fe7bdffe66d9_fb35b5b8 = memo(({children}) => {
    const on_click_2953ef10befce8cf7026f08468889473 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_age_bracket", ({ ["val"] : "46-60" }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesButton,{css:({ ["width"] : "100%", ["minHeight"] : "48px" }),onClick:on_click_2953ef10befce8cf7026f08468889473,variant:((reflex___state____state__preconsult___state____state.age_bracket_rx_state_?.valueOf?.() === "46-60"?.valueOf?.()) ? "solid" : "outline")},children)
    )
});

export const Button_button_1910876bad26fe9db615ad25cfb73005_fb35b5b8 = memo(({children}) => {
    const on_click_a702896a7083b1e4b06bb5e24a374b1e = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_age_bracket", ({ ["val"] : "60+" }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesButton,{css:({ ["width"] : "100%", ["minHeight"] : "48px" }),onClick:on_click_a702896a7083b1e4b06bb5e24a374b1e,variant:((reflex___state____state__preconsult___state____state.age_bracket_rx_state_?.valueOf?.() === "60+"?.valueOf?.()) ? "solid" : "outline")},children)
    )
});

export const Bare_comp_94b07c05b6c743acea49bd73f7732a7f_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["gender"]
    )
});

export const Bare_comp_f1e32fa5a810ddb8026f726e460aaf0d_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["gender_select_sr"]
    )
});

export const Selecttrigger_select__trigger_a84be15050924f5a469a08603664ffa3_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesSelect.Trigger,{css:({ ["width"] : "100%" }),placeholder:reflex___state____state__preconsult___state____state.t_rx_state_?.["gender_ph"]},)
    )
});

export const Foreach_comp_25caf85546f8505b5e68830fbbdf7882_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        Array.prototype.map.call(reflex___state____state__preconsult___state____state.gender_opts_rx_state_ ?? [],((item_rx_state_,index_9823cf83aa70cfbb1602bac35e8f2f1e)=>(jsx(RadixThemesSelect.Item,{key:index_9823cf83aa70cfbb1602bac35e8f2f1e,value:item_rx_state_},item_rx_state_))))
    )
});

export const Selectroot_select__root_9da43587f69131eb43c6fa2e08105e2e_fb35b5b8 = memo(({children}) => {
    const on_change_b9194a2140b749a9c74429cf1bf7a48d = useCallback(((_ev_0) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_gender", ({ ["val"] : _ev_0 }), ({  })))], [_ev_0], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesSelect.Root,{"aria-label":"Select your gender",css:({ ["minHeight"] : "48px" }),onValueChange:on_change_b9194a2140b749a9c74429cf1bf7a48d,value:reflex___state____state__preconsult___state____state.gender_rx_state_},children)
    )
});

export const Bare_comp_c8723900cfbb4c4c042cb2d15e8663e5_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["start_btn"]
    )
});

export const Button_button_dce2ad1722b9a4159c94224b5129258f_fb35b5b8 = memo(({children}) => {
    const on_click_bd25bb776995b5675a1b30175a9149fa = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.go_to_step_2", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])



    return(
        jsx(RadixThemesButton,{color:"cyan",css:({ ["width"] : "100%", ["minHeight"] : "48px", ["&:hover"] : ({ ["transform"] : "scale(1.02)", ["background"] : "cyan.600" }), ["transition"] : "all 0.2s ease", ["animation"] : "fadeInUp 0.4s ease-out 0.2s both" }),onClick:on_click_bd25bb776995b5675a1b30175a9149fa,size:"4"},children)
    )
});

export const Bare_comp_77b5e2be3d1fe915231e1a985b77aab8_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["privacy_step_note"]
    )
});

export const Bare_comp_0e985dd0d897d99e3117271ae677304a_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_1"]
    )
});

export const Bare_comp_159d88d732804ed5f539366438fbad13_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_1_desc"]
    )
});

export const Bare_comp_cab943bd9d71ba40c4a492ced3464475_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["concern"]
    )
});

export const Debounceinput_debounceinput_477288a1a3eb0a16ba6449fdb6b4a640_fb35b5b8 = memo(({children}) => {
    const on_change_7240b87dba6e1ec9d937fd4bc863092c = useCallback(((_e) => {(addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_chief_complaint", ({ ["val"] : _e?.["target"]?.["value"] }), ({  })))], [_e], ({  })));(addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_complaint_detail", ({ ["val"] : "" }), ({  })))], [_e], ({  })));}), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(DebounceInput,{"aria-label":"Chief Complaint",css:({ ["width"] : "100%", ["height"] : "80px", ["minHeight"] : "48px" }),debounceTimeout:300,element:RadixThemesTextArea,onChange:on_change_7240b87dba6e1ec9d937fd4bc863092c,placeholder:reflex___state____state__preconsult___state____state.t_rx_state_?.["concern_ph"],value:reflex___state____state__preconsult___state____state.chief_complaint_rx_state_},)
    )
});

export const Bare_comp_6c35c2b7379b5a4f0038bc8af8fd8a37_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["duration"]
    )
});

export const Foreach_comp_2c27ebac61b1c1c4c0d00c5dcd687d5f_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        Array.prototype.map.call(reflex___state____state__preconsult___state____state.duration_opts_with_keys_rx_state_ ?? [],((opt_rx_state_,index_36f22d71ba3e4b8f1580f4653cc6a892)=>(jsx(RadixThemesButton,{css:({ ["width"] : "100%", ["minHeight"] : "48px" }),key:index_36f22d71ba3e4b8f1580f4653cc6a892,onClick:((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_duration", ({ ["val"] : opt_rx_state_?.["id"] }), ({  })))], [_e], ({  })))),variant:((reflex___state____state__preconsult___state____state.duration_rx_state_?.valueOf?.() === opt_rx_state_?.["id"]?.valueOf?.()) ? "solid" : "outline")},opt_rx_state_?.["label"]))))
    )
});

export const Bare_comp_a4227c3c507e15a5fc7384bbcef68c8d_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["specialist"]
    )
});

export const Debounceinput_debounceinput_00588a6a7281ffcb3f13f22d52ae64f4_fb35b5b8 = memo(({children}) => {
    const on_change_785c2664f397d047225621260aee0375 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_specialist", ({ ["val"] : _e?.["target"]?.["value"] }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(DebounceInput,{"aria-label":"Specialist you are seeing",css:({ ["width"] : "100%", ["minHeight"] : "48px" }),debounceTimeout:300,element:RadixThemesTextField.Root,onChange:on_change_785c2664f397d047225621260aee0375,placeholder:reflex___state____state__preconsult___state____state.t_rx_state_?.["specialist_ph"],value:(isNotNullOrUndefined(reflex___state____state__preconsult___state____state.specialist_rx_state_) ? reflex___state____state__preconsult___state____state.specialist_rx_state_ : "")},)
    )
});

export const Bare_comp_14402f43665e1cb44c84e46c6d31c877_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["back_btn"]
    )
});

export const Button_button_d47038ebff5ddddbbe63b2f180432a5d_fb35b5b8 = memo(({children}) => {
    const on_click_c9cb50eb73f67d60c328ead9e8f6a85e = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.go_back", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])



    return(
        jsx(RadixThemesButton,{color:"gray",css:({ ["width"] : "100%", ["minHeight"] : "48px" }),onClick:on_click_c9cb50eb73f67d60c328ead9e8f6a85e,size:"4",variant:"outline"},children)
    )
});

export const Button_button_df047e8331f067e8587baf6d1b05462a_fb35b5b8 = memo(({children}) => {
    const on_click_1c577c5964627c437110672c02c9063a = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.go_to_step_3", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])



    return(
        jsx(RadixThemesButton,{color:"cyan",css:({ ["width"] : "100%", ["minHeight"] : "48px" }),loading:false,onClick:on_click_1c577c5964627c437110672c02c9063a,size:"4"},children)
    )
});

export const Bare_comp_94f6d5abea727676b70e452905177009_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_2"]
    )
});

export const Bare_comp_39d6ad0878b2e715312be085a99af919_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_2_desc"]
    )
});

export const Bare_comp_512cf56cd5d3b0225cca740e6a606671_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["conditions_label"]
    )
});

export const Foreach_comp_68a6c9b836e3de5d22e6d916a91a478f_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        Array.prototype.map.call(reflex___state____state__preconsult___state____state.conditions_opts_with_keys_rx_state_ ?? [],((opt_rx_state_,index_d86a1962dcaaa1e1db8e74dd5d0e92e9)=>(jsx(RadixThemesButton,{css:({ ["width"] : "100%", ["minHeight"] : "48px" }),key:index_d86a1962dcaaa1e1db8e74dd5d0e92e9,onClick:((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.toggle_condition", ({ ["condition"] : opt_rx_state_?.["id"] }), ({  })))], [_e], ({  })))),variant:(reflex___state____state__preconsult___state____state.conditions_rx_state_.includes(opt_rx_state_?.["id"]) ? "solid" : "outline")},opt_rx_state_?.["label"]))))
    )
});

export const Bare_comp_792d575c4e9af09bc819c5cf431a93b3_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["conditions_none"]
    )
});

export const Button_button_15cd4740f4a1d4b56c8003e803645fbb_fb35b5b8 = memo(({children}) => {
    const on_click_b23fb442e0dfa84ab259ec9b26d50502 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.clear_conditions", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesButton,{color:"gray",css:({ ["width"] : "100%", ["minHeight"] : "48px" }),onClick:on_click_b23fb442e0dfa84ab259ec9b26d50502,variant:((reflex___state____state__preconsult___state____state.conditions_rx_state_.length?.valueOf?.() === 0?.valueOf?.()) ? "solid" : "outline")},children)
    )
});

export const Bare_comp_5c47fd8f641de64d328209fba7fde637_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["medications_label"]
    )
});

export const Foreach_comp_cc4aaeba89a63257d5e76b16bd48332d_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        Array.prototype.map.call(reflex___state____state__preconsult___state____state.medications_rx_state_ ?? [],((m_rx_state_,i_rx_state_)=>(jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"row",key:i_rx_state_,gap:"2"},jsx(DebounceInput,{"aria-label":"Medication name",css:({ ["flex"] : "1", ["minHeight"] : "48px" }),debounceTimeout:300,element:RadixThemesTextField.Root,onChange:((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.update_medication", ({ ["idx"] : i_rx_state_, ["val"] : _e?.["target"]?.["value"] }), ({  })))], [_e], ({  })))),placeholder:reflex___state____state__preconsult___state____state.t_rx_state_?.["medications_ph"],value:(isNotNullOrUndefined(reflex___state____state__preconsult___state____state.medications_rx_state_?.at?.(i_rx_state_)) ? reflex___state____state__preconsult___state____state.medications_rx_state_?.at?.(i_rx_state_) : "")},),jsx(RadixThemesButton,{"aria-label":"Remove medication",color:"red",css:({ ["minHeight"] : "48px", ["width"] : ({ ["initial"] : "48px", ["sm"] : "auto" }) }),onClick:((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.remove_medication", ({ ["idx"] : i_rx_state_ }), ({  })))], [_e], ({  })))),variant:"outline"},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["alignItems"] : "center" }),direction:"row",gap:"2"},jsx(LucideTrash,{size:16},),jsx(RadixThemesText,{as:"p",css:({ ["display"] : ({ ["initial"] : "none", ["sm"] : "block" }) })},reflex___state____state__preconsult___state____state.t_rx_state_?.["remove"])))))))
    )
});

export const Cond_comp_f4fc3af41548da57c1560ab27232b79a_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        ((reflex___state____state__preconsult___state____state.medications_rx_state_.length > 0)?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Bare_comp_34d041ec18e1bb2850c2016598a22fad_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["add_medication"]
    )
});

export const Button_button_33bc532b1029b8deae165944334bdf9f_fb35b5b8 = memo(({children}) => {
    const on_click_b776f7c96ba103d5ab833cf6934d54fa = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.add_medication", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])



    return(
        jsx(RadixThemesButton,{css:({ ["minHeight"] : "48px" }),onClick:on_click_b776f7c96ba103d5ab833cf6934d54fa,variant:"ghost"},children)
    )
});

export const Bare_comp_826632e84bb5681febcc74448fc1baa1_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_label"]
    )
});

export const Bare_comp_9fadee35c125b491e10a54cf3ad92932_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_no"]
    )
});

export const Segmentedcontrolitem_segmentedcontrol__item_3ee48785d9c04b99a00ee30d0999090f_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesSegmentedControl.Item,{css:({ ["minHeight"] : "48px" }),value:reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_no"]},children)
    )
});

export const Bare_comp_b97692df1ee270b1f45e7c4c6c66c73d_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_yes"]
    )
});

export const Segmentedcontrolitem_segmentedcontrol__item_c073c99e6ac2e79c69c2ecb76778c88b_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesSegmentedControl.Item,{css:({ ["minHeight"] : "48px" }),value:reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_yes"]},children)
    )
});

export const Segmentedcontrolroot_segmentedcontrol__root_0b241a4dd7c55a4922abbc625336796a_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)
const on_change_7c66f2276415bb2892b3f34b84c73bea = useCallback(((_value) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_allergies_flag", ({ ["val"] : (reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_yes"]?.valueOf?.() === _value?.valueOf?.()) }), ({  })))], [_value], ({  })))), [addEvents, ReflexEvent, reflex___state____state__preconsult___state____state])



    return(
        jsx(RadixThemesSegmentedControl.Root,{"aria-label":"Do you have any drug allergies?",css:({ ["& .rt-SegmentedControlIndicator"] : ({ ["width"] : "calc(100% / var(--rx-sc-count))", ["transform"] : "translateX(calc(var(--rx-sc-idx) * 100%))" }), ["--rx-sc-count"] : [reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_no"], reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_yes"]].length, ["--rx-sc-idx"] : ([reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_no"], reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_yes"]].indexOf((reflex___state____state__preconsult___state____state.allergies_flag_rx_state_ ? reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_yes"] : reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_no"]))), ["width"] : "100%" }),onValueChange:on_change_7c66f2276415bb2892b3f34b84c73bea,value:(reflex___state____state__preconsult___state____state.allergies_flag_rx_state_ ? reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_yes"] : reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_no"])},children)
    )
});

export const Debounceinput_debounceinput_b53747022743c487cbedb8cbd7830678_fb35b5b8 = memo(({children}) => {
    const on_change_3d9c8565c3b144db644f888fe21804ec = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_allergies_text", ({ ["val"] : _e?.["target"]?.["value"] }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(DebounceInput,{"aria-label":"List your drug allergies",css:({ ["width"] : "100%", ["minHeight"] : "48px", ["animation"] : "fadeInUp 0.2s ease-out both" }),debounceTimeout:300,element:RadixThemesTextArea,onChange:on_change_3d9c8565c3b144db644f888fe21804ec,placeholder:reflex___state____state__preconsult___state____state.t_rx_state_?.["allergies_ph"],value:reflex___state____state__preconsult___state____state.allergies_text_rx_state_},)
    )
});

export const Cond_comp_290f511549e6d1d0b671ba71e866d3ce_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        (reflex___state____state__preconsult___state____state.allergies_flag_rx_state_?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Button_button_532a4dfde775983b7af64fc36b7efc67_fb35b5b8 = memo(({children}) => {
    const on_click_f0279763430e8d13fabeed124582cca3 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.go_to_step_4", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])



    return(
        jsx(RadixThemesButton,{color:"cyan",css:({ ["width"] : "100%", ["minHeight"] : "48px" }),loading:false,onClick:on_click_f0279763430e8d13fabeed124582cca3,size:"4"},children)
    )
});

export const Bare_comp_66a337b1394384073cc7deaf5c1d4293_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_3"]
    )
});

export const Bare_comp_4a68344e6b96f52a6660304980f4a296_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_3_desc"]
    )
});

export const Bare_comp_085950b5798854a9b671bd49c98939f5_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["family_history_label"]
    )
});

export const Foreach_comp_f7515f7c70c4a87abf07fb7be24e8804_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        Array.prototype.map.call(reflex___state____state__preconsult___state____state.family_history_opts_with_keys_rx_state_ ?? [],((opt_rx_state_,index_d86a1962dcaaa1e1db8e74dd5d0e92e9)=>(jsx(RadixThemesButton,{css:({ ["width"] : "100%", ["minHeight"] : "48px" }),key:index_d86a1962dcaaa1e1db8e74dd5d0e92e9,onClick:((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.toggle_family_history", ({ ["item"] : opt_rx_state_?.["id"] }), ({  })))], [_e], ({  })))),variant:(reflex___state____state__preconsult___state____state.family_history_rx_state_.includes(opt_rx_state_?.["id"]) ? "solid" : "outline")},opt_rx_state_?.["label"]))))
    )
});

export const Bare_comp_1ced90fd2c91abb81a8052f11083ed31_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["smoking_label"]
    )
});

export const Foreach_comp_546d4159a7ddc10eacdfc1c1108be2b5_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        Array.prototype.map.call(reflex___state____state__preconsult___state____state.smoking_opts_with_keys_rx_state_ ?? [],((opt_rx_state_,index_36f22d71ba3e4b8f1580f4653cc6a892)=>(jsx(RadixThemesButton,{css:({ ["width"] : "100%", ["minHeight"] : "48px" }),key:index_36f22d71ba3e4b8f1580f4653cc6a892,onClick:((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_smoking", ({ ["val"] : opt_rx_state_?.["id"] }), ({  })))], [_e], ({  })))),variant:((reflex___state____state__preconsult___state____state.smoking_rx_state_?.valueOf?.() === opt_rx_state_?.["id"]?.valueOf?.()) ? "solid" : "outline")},opt_rx_state_?.["label"]))))
    )
});

export const Bare_comp_3cd58acf4f76a3dc77cf3dc9cdf7e7f1_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["alcohol_label"]
    )
});

export const Foreach_comp_84d0b0f98c9d199c67a6a85631254019_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        Array.prototype.map.call(reflex___state____state__preconsult___state____state.alcohol_opts_with_keys_rx_state_ ?? [],((opt_rx_state_,index_36f22d71ba3e4b8f1580f4653cc6a892)=>(jsx(RadixThemesButton,{css:({ ["width"] : "100%", ["minHeight"] : "48px" }),key:index_36f22d71ba3e4b8f1580f4653cc6a892,onClick:((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_alcohol", ({ ["val"] : opt_rx_state_?.["id"] }), ({  })))], [_e], ({  })))),variant:((reflex___state____state__preconsult___state____state.alcohol_rx_state_?.valueOf?.() === opt_rx_state_?.["id"]?.valueOf?.()) ? "solid" : "outline")},opt_rx_state_?.["label"]))))
    )
});

export const Bare_comp_8798c09f630f4f5c47e6c7b8f93e6770_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["generate_qs_btn"]
    )
});

export const Button_button_8a67648184de12fca6cab44913623ac9_fb35b5b8 = memo(({children}) => {
    const on_click_81359646bbbc62b3cc0a65b2f80cd859 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.init_session", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesButton,{color:"cyan",css:({ ["width"] : "100%", ["minHeight"] : "48px" }),loading:reflex___state____state__preconsult___state____state.loading_rx_state_,onClick:on_click_81359646bbbc62b3cc0a65b2f80cd859,size:"4"},children)
    )
});

export const Bare_comp_877eacc5466091dccf6371af60206e3f_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_4"]
    )
});

export const Bare_comp_40d2a83371e9bbbc8c6acf98d6de8168_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["step_4_desc"]
    )
});

export const Foreach_comp_6c561c61a7e2bda7978e2dd80c7e2f3d_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        Array.prototype.map.call(reflex___state____state__preconsult___state____state.questions_rx_state_ ?? [],((q_rx_state_,i_rx_state_)=>(jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%" }),direction:"column",key:i_rx_state_,gap:"3"},jsx(RadixThemesText,{as:"p",color:"gray",size:"2",weight:"bold"},("Question "+(i_rx_state_ + 1)+" of "+reflex___state____state__preconsult___state____state.questions_rx_state_.length)),jsx(RadixThemesText,{as:"p",weight:"bold"},q_rx_state_),jsx(DebounceInput,{"aria-label":"Answer for clinical question",css:({ ["width"] : "100%", ["height"] : "80px", ["minHeight"] : "48px" }),debounceTimeout:300,element:RadixThemesTextArea,onChange:((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_answer", ({ ["idx"] : i_rx_state_, ["val"] : _e?.["target"]?.["value"] }), ({  })))], [_e], ({  })))),onFocus:((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.set_question_index", ({ ["idx"] : i_rx_state_ }), ({  })))], [_e], ({  })))),placeholder:reflex___state____state__preconsult___state____state.t_rx_state_?.["answers_ph"],value:reflex___state____state__preconsult___state____state.current_answers_rx_state_?.at?.(i_rx_state_)},)))))
    )
});

export const Cond_comp_77cac4595e3a6aeb8e75b95cd3277f77_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        ((reflex___state____state__preconsult___state____state.questions_rx_state_.length > 0)?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Bare_comp_bdf60041c043164860364ab0b0682440_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["emergency_title"]
    )
});

export const Bare_comp_007f09781493e5fd4c7b2f342c873be0_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["emergency_body"]
    )
});

export const Bare_comp_c06e9cd39cbfb5cf89884d6163621e49_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["emergency_cta"]
    )
});

export const Button_button_593e67325a477ffb5353ec48d5c6bf3a_fb35b5b8 = memo(({children}) => {
    const on_click_8552f88a33a715f92112f009d36a6cf6 = useCallback(((_e) => (addEvents([(ReflexEvent("_redirect", ({ ["path"] : "/", ["external"] : false, ["popup"] : false, ["replace"] : false }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])



    return(
        jsx(RadixThemesButton,{color:"red",css:({ ["width"] : "100%", ["minHeight"] : "48px" }),onClick:on_click_8552f88a33a715f92112f009d36a6cf6,variant:"solid"},children)
    )
});

export const Cond_comp_0b0212c3ce7ae1ccbe366dfe6445df30_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        (reflex___state____state__preconsult___state____state.is_emergency_rx_state_?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Bare_comp_68caa840ba7adca4cf4baa474345ec84_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["submit_continue"]
    )
});

export const Button_button_d674506f1105ff9a03516bd3f617ad4f_fb35b5b8 = memo(({children}) => {
    const on_click_fc7c3253d9cb770d2b09bb67bfc03d53 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.submit_answers", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesButton,{color:"cyan",css:({ ["width"] : "100%", ["minHeight"] : "48px" }),loading:reflex___state____state__preconsult___state____state.loading_rx_state_,onClick:on_click_fc7c3253d9cb770d2b09bb67bfc03d53,size:"4"},children)
    )
});

export const Bare_comp_88105c70110c7000ec5d09966d2c5930_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["complete_title"]
    )
});

export const Bare_comp_a5211812978e116576f91a0065622607_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["complete_desc"]
    )
});

export const Bare_comp_c8d093cc1e2454338ef85fa82c4efa84_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["download_btn"]
    )
});

export const Button_button_1688571e2198a5938767878552d62670_fb35b5b8 = memo(({children}) => {
    const on_click_38ad705f0b0e6f65e00507b9bef9f558 = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.download_report", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])
const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesButton,{color:"green",css:({ ["width"] : "100%", ["padding"] : "1.5em", ["minHeight"] : "48px", ["&:hover"] : ({ ["transform"] : "scale(1.02)" }), ["transition"] : "all 0.2s ease" }),loading:reflex___state____state__preconsult___state____state.loading_rx_state_,onClick:on_click_38ad705f0b0e6f65e00507b9bef9f558,size:"4"},children)
    )
});

export const Bare_comp_2e9dcc816e6de5662bb0aa5d0414f9e7_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["copy_btn"]
    )
});

export const Button_button_9bfb140b00e80745da34d523e1edccff_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)
const on_click_0de51e66d24418b8a3ece2d881c0023d = useCallback(((_e) => (addEvents([(ReflexEvent("_call_function", ({ ["function"] : (() => (navigator?.["clipboard"]?.["writeText"](reflex___state____state__preconsult___state____state.summary_text_rx_state_))), ["callback"] : null }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent, reflex___state____state__preconsult___state____state])



    return(
        jsx(RadixThemesButton,{color:"blue",css:({ ["width"] : "100%", ["minHeight"] : "48px" }),onClick:on_click_0de51e66d24418b8a3ece2d881c0023d,size:"4",variant:"outline"},children)
    )
});

export const Bare_comp_68f8381a9fb0ce22d47e87fafc77663a_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["start_new"]
    )
});

export const Button_button_f86ad5572178fda40bfb298c300b30c6_fb35b5b8 = memo(({children}) => {
    const on_click_5a9a991a00b3513d43b3402fcdaf4e8f = useCallback(((_e) => (addEvents([(ReflexEvent("reflex___state____state.preconsult___state____state.reset_intake", ({  }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])



    return(
        jsx(RadixThemesButton,{color:"gray",css:({ ["width"] : "100%", ["minHeight"] : "48px", ["&:hover"] : ({ ["transform"] : "scale(1.02)" }), ["transition"] : "all 0.2s ease" }),onClick:on_click_5a9a991a00b3513d43b3402fcdaf4e8f,variant:"ghost"},children)
    )
});

export const Bare_comp_80f04de160f71d509d12aea21c6ce592_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["privacy_badge"]
    )
});

export const Match_comp_b9dc58b459198953d0d4f5f277e863ad_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        (() => {
  switch (JSON.stringify(reflex___state____state__preconsult___state____state.step_rx_state_)) {
    case JSON.stringify(0):
      return children?.at?.(0);
      break;
    case JSON.stringify(1):
      return children?.at?.(1);
      break;
    case JSON.stringify(2):
      return children?.at?.(2);
      break;
    case JSON.stringify(3):
      return children?.at?.(3);
      break;
    case JSON.stringify(4):
      return children?.at?.(4);
      break;
    case JSON.stringify(5):
      return children?.at?.(5);
      break;
    case JSON.stringify(6):
      return children?.at?.(6);
      break;
    default:
      return children?.at?.(7);
      break;
  }
})()
    )
});

export const Card_card_bc64d2beb6e32d351d065a2b7c5985f5_fb35b5b8 = memo(({children}) => {
    const { rawColorMode } = useContext(ColorModeContext)



    return(
        jsx(RadixThemesCard,{css:({ ["padding"] : ({ ["initial"] : "1.5em", ["sm"] : "1.5em", ["md"] : "2em" }), ["width"] : "100%", ["background"] : ((rawColorMode?.valueOf?.() === "light"?.valueOf?.()) ? "rgba(255,255,255,0.92)" : "rgba(13, 27, 42, 0.85)"), ["backdropFilter"] : "blur(15px)", ["border"] : ((rawColorMode?.valueOf?.() === "light"?.valueOf?.()) ? "1px solid rgba(0,0,0,0.08)" : "1px solid rgba(255,255,255,0.1)"), ["borderRadius"] : "20px", ["boxShadow"] : ((rawColorMode?.valueOf?.() === "light"?.valueOf?.()) ? "0 8px 32px 0 rgba(0,0,0,0.08)" : "0 8px 32px 0 rgba(0,0,0,0.37)") })},children)
    )
});

export const Bare_comp_87309c371017f6791d754b379a6fcc85_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["faq_title"]
    )
});

export const Accordiontrigger_trigger_602d64623a28564635d95e8f1420f91c_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixAccordionTrigger,{className:"AccordionTrigger",css:({ ["color"] : "var(--accent-11)", ["fontSize"] : "1.1em", ["lineHeight"] : 1, ["justifyContent"] : "space-between", ["alignItems"] : "center", ["flex"] : 1, ["display"] : "flex", ["padding"] : "0.85em 1em", ["width"] : "100%", ["boxShadow"] : "0 var(--divider-px) 0 var(--gray-a6)", ["&[data-state='open'] > .AccordionChevron"] : ({ ["transform"] : "rotate(180deg)" }), ["&:hover"] : ({ ["background"] : "rgba(0, 200, 255, 0.04)" }), ["& > .AccordionChevron"] : ({ ["transition"] : "transform var(--animation-duration) var(--animation-easing)" }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)", ["&:hover"] : ({ ["backgroundColor"] : "var(--accent-10)" }), ["& > .AccordionChevron"] : ({ ["color"] : "var(--accent-contrast)" }) }), ["background"] : "none", ["border"] : "none", ["cursor"] : "pointer", ["borderRadius"] : "8px" })},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%", ["alignItems"] : "center" }),direction:"row",gap:"3"},jsx(RadixThemesText,{as:"p",size:"3",weight:"bold"},reflex___state____state__preconsult___state____state.t_rx_state_?.["faq_q1"]),jsx(RadixThemesFlex,{css:({ ["flex"] : 1, ["justifySelf"] : "stretch", ["alignSelf"] : "stretch" })},),jsx(LucideChevronDown,{size:16},)))
    )
});

export const Bare_comp_541b77f033b20cb4b55f5cfa6729291f_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["faq_a1"]
    )
});

export const Accordiontrigger_trigger_66be306ca0efbd51b08a2ba93519ea86_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixAccordionTrigger,{className:"AccordionTrigger",css:({ ["color"] : "var(--accent-11)", ["fontSize"] : "1.1em", ["lineHeight"] : 1, ["justifyContent"] : "space-between", ["alignItems"] : "center", ["flex"] : 1, ["display"] : "flex", ["padding"] : "0.85em 1em", ["width"] : "100%", ["boxShadow"] : "0 var(--divider-px) 0 var(--gray-a6)", ["&[data-state='open'] > .AccordionChevron"] : ({ ["transform"] : "rotate(180deg)" }), ["&:hover"] : ({ ["background"] : "rgba(0, 200, 255, 0.04)" }), ["& > .AccordionChevron"] : ({ ["transition"] : "transform var(--animation-duration) var(--animation-easing)" }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)", ["&:hover"] : ({ ["backgroundColor"] : "var(--accent-10)" }), ["& > .AccordionChevron"] : ({ ["color"] : "var(--accent-contrast)" }) }), ["background"] : "none", ["border"] : "none", ["cursor"] : "pointer", ["borderRadius"] : "8px" })},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%", ["alignItems"] : "center" }),direction:"row",gap:"3"},jsx(RadixThemesText,{as:"p",size:"3",weight:"bold"},reflex___state____state__preconsult___state____state.t_rx_state_?.["faq_q2"]),jsx(RadixThemesFlex,{css:({ ["flex"] : 1, ["justifySelf"] : "stretch", ["alignSelf"] : "stretch" })},),jsx(LucideChevronDown,{size:16},)))
    )
});

export const Bare_comp_773f3ec7ed198e007dbfefa3bd4a970f_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["faq_a2"]
    )
});

export const Accordiontrigger_trigger_4a3284473309d706d062116e6469e0c9_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixAccordionTrigger,{className:"AccordionTrigger",css:({ ["color"] : "var(--accent-11)", ["fontSize"] : "1.1em", ["lineHeight"] : 1, ["justifyContent"] : "space-between", ["alignItems"] : "center", ["flex"] : 1, ["display"] : "flex", ["padding"] : "0.85em 1em", ["width"] : "100%", ["boxShadow"] : "0 var(--divider-px) 0 var(--gray-a6)", ["&[data-state='open'] > .AccordionChevron"] : ({ ["transform"] : "rotate(180deg)" }), ["&:hover"] : ({ ["background"] : "rgba(0, 200, 255, 0.04)" }), ["& > .AccordionChevron"] : ({ ["transition"] : "transform var(--animation-duration) var(--animation-easing)" }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)", ["&:hover"] : ({ ["backgroundColor"] : "var(--accent-10)" }), ["& > .AccordionChevron"] : ({ ["color"] : "var(--accent-contrast)" }) }), ["background"] : "none", ["border"] : "none", ["cursor"] : "pointer", ["borderRadius"] : "8px" })},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%", ["alignItems"] : "center" }),direction:"row",gap:"3"},jsx(RadixThemesText,{as:"p",size:"3",weight:"bold"},reflex___state____state__preconsult___state____state.t_rx_state_?.["faq_q3"]),jsx(RadixThemesFlex,{css:({ ["flex"] : 1, ["justifySelf"] : "stretch", ["alignSelf"] : "stretch" })},),jsx(LucideChevronDown,{size:16},)))
    )
});

export const Bare_comp_77dc045a2c2ebd626d86d71ac16e5bc4_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["faq_a3"]
    )
});

export const Accordiontrigger_trigger_60f375d87fc80845be52b7c5b0dc7cad_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixAccordionTrigger,{className:"AccordionTrigger",css:({ ["color"] : "var(--accent-11)", ["fontSize"] : "1.1em", ["lineHeight"] : 1, ["justifyContent"] : "space-between", ["alignItems"] : "center", ["flex"] : 1, ["display"] : "flex", ["padding"] : "0.85em 1em", ["width"] : "100%", ["boxShadow"] : "0 var(--divider-px) 0 var(--gray-a6)", ["&[data-state='open'] > .AccordionChevron"] : ({ ["transform"] : "rotate(180deg)" }), ["&:hover"] : ({ ["background"] : "rgba(0, 200, 255, 0.04)" }), ["& > .AccordionChevron"] : ({ ["transition"] : "transform var(--animation-duration) var(--animation-easing)" }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)", ["&:hover"] : ({ ["backgroundColor"] : "var(--accent-10)" }), ["& > .AccordionChevron"] : ({ ["color"] : "var(--accent-contrast)" }) }), ["background"] : "none", ["border"] : "none", ["cursor"] : "pointer", ["borderRadius"] : "8px" })},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%", ["alignItems"] : "center" }),direction:"row",gap:"3"},jsx(RadixThemesText,{as:"p",size:"3",weight:"bold"},reflex___state____state__preconsult___state____state.t_rx_state_?.["faq_q4"]),jsx(RadixThemesFlex,{css:({ ["flex"] : 1, ["justifySelf"] : "stretch", ["alignSelf"] : "stretch" })},),jsx(LucideChevronDown,{size:16},)))
    )
});

export const Bare_comp_472eec879efa87326960e562b6dee8f0_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["faq_a4"]
    )
});

export const Accordiontrigger_trigger_c221ff9df2c7e843cc4c83e7d780fc9c_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixAccordionTrigger,{className:"AccordionTrigger",css:({ ["color"] : "var(--accent-11)", ["fontSize"] : "1.1em", ["lineHeight"] : 1, ["justifyContent"] : "space-between", ["alignItems"] : "center", ["flex"] : 1, ["display"] : "flex", ["padding"] : "0.85em 1em", ["width"] : "100%", ["boxShadow"] : "0 var(--divider-px) 0 var(--gray-a6)", ["&[data-state='open'] > .AccordionChevron"] : ({ ["transform"] : "rotate(180deg)" }), ["&:hover"] : ({ ["background"] : "rgba(0, 200, 255, 0.04)" }), ["& > .AccordionChevron"] : ({ ["transition"] : "transform var(--animation-duration) var(--animation-easing)" }), ["&[data-variant='classic'], *:where([data-variant='classic']) &"] : ({ ["color"] : "var(--accent-contrast)", ["&:hover"] : ({ ["backgroundColor"] : "var(--accent-10)" }), ["& > .AccordionChevron"] : ({ ["color"] : "var(--accent-contrast)" }) }), ["background"] : "none", ["border"] : "none", ["cursor"] : "pointer", ["borderRadius"] : "8px" })},jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%", ["alignItems"] : "center" }),direction:"row",gap:"3"},jsx(RadixThemesText,{as:"p",size:"3",weight:"bold"},reflex___state____state__preconsult___state____state.t_rx_state_?.["faq_q5"]),jsx(RadixThemesFlex,{css:({ ["flex"] : 1, ["justifySelf"] : "stretch", ["alignSelf"] : "stretch" })},),jsx(LucideChevronDown,{size:16},)))
    )
});

export const Bare_comp_38a4f8bf4e3890168dee724535d4207c_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["faq_a5"]
    )
});

export const Bare_comp_136f4d94fe994cc39972e8bd14af1975_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        reflex___state____state__preconsult___state____state.t_rx_state_?.["footer_disclaimer"]
    )
});

export const Link_link_7b550eb708f87a5adc7ae527c6283577_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesLink,{asChild:true,color:"cyan",css:({ ["&:hover"] : ({ ["color"] : "var(--accent-8)" }) }),size:"2"},jsx(ReactRouterLink,{to:"/privacy"},reflex___state____state__preconsult___state____state.t_rx_state_?.["footer_privacy"]))
    )
});

export const Link_link_231fec93d892bd9b498f69d4f00676b1_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____state = useContext(StateContexts.reflex___state____state__preconsult___state____state)



    return(
        jsx(RadixThemesLink,{asChild:true,color:"cyan",css:({ ["&:hover"] : ({ ["color"] : "var(--accent-8)" }) }),size:"2"},jsx(ReactRouterLink,{to:"/terms"},reflex___state____state__preconsult___state____state.t_rx_state_?.["footer_terms"]))
    )
});

export const Vstack_flex_f4bab62a7587104b9b52cd373d4d8f69_fb35b5b8 = memo(({children}) => {
    const { rawColorMode } = useContext(ColorModeContext)



    return(
        jsx(RadixThemesFlex,{align:"start",className:"rx-Stack",css:({ ["width"] : "100%", ["minHeight"] : "100vh", ["alignItems"] : "center", ["background"] : ((rawColorMode?.valueOf?.() === "light"?.valueOf?.()) ? "radial-gradient(circle at top right, #f8fafc, #f1f5f9, #e2e8f0)" : "radial-gradient(circle at top right, #0a192f, #001f3f, #001529)") }),direction:"column",gap:"3"},children)
    )
});

export const Foreach_comp_5ce5fab84cf37f6a7970463016d1da0e_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____admin_state = useContext(StateContexts.reflex___state____state__preconsult___state____admin_state)



    return(
        Array.prototype.map.call(reflex___state____state__preconsult___state____admin_state.analytics_data_rx_state_ ?? [],((row_rx_state_,index_1e85e3f334e28949b38666cf27792c05)=>(jsx(RadixThemesTable.Row,{key:index_1e85e3f334e28949b38666cf27792c05},jsx(RadixThemesTable.Cell,{},row_rx_state_?.["date"]),jsx(RadixThemesTable.Cell,{},row_rx_state_?.["demographics"]),jsx(RadixThemesTable.Cell,{},row_rx_state_?.["complaint"]),jsx(RadixThemesTable.Cell,{},row_rx_state_?.["history"]),jsx(RadixThemesTable.Cell,{},row_rx_state_?.["lifestyle"]),jsx(RadixThemesTable.Cell,{},row_rx_state_?.["summary"]),jsx(RadixThemesTable.Cell,{},row_rx_state_?.["pdf"])))))
    )
});

export const Button_button_017d529b4de1fc08cad251e0f5d94ce4_fb35b5b8 = memo(({children}) => {
    const on_click_8552f88a33a715f92112f009d36a6cf6 = useCallback(((_e) => (addEvents([(ReflexEvent("_redirect", ({ ["path"] : "/", ["external"] : false, ["popup"] : false, ["replace"] : false }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])



    return(
        jsx(RadixThemesButton,{color:"cyan",onClick:on_click_8552f88a33a715f92112f009d36a6cf6,size:"3"},children)
    )
});

export const Button_button_e9634e9129c5fef32f633aa2241a15aa_fb35b5b8 = memo(({children}) => {
    const on_click_8552f88a33a715f92112f009d36a6cf6 = useCallback(((_e) => (addEvents([(ReflexEvent("_redirect", ({ ["path"] : "/", ["external"] : false, ["popup"] : false, ["replace"] : false }), ({  })))], [_e], ({  })))), [addEvents, ReflexEvent])



    return(
        jsx(RadixThemesButton,{color:"gray",onClick:on_click_8552f88a33a715f92112f009d36a6cf6,size:"3"},children)
    )
});

export const Cond_comp_202fae3e2d8d9ea4791e8b4294ae523b_fb35b5b8 = memo(({children}) => {
    const reflex___state____state__preconsult___state____admin_state = useContext(StateContexts.reflex___state____state__preconsult___state____admin_state)



    return(
        (reflex___state____state__preconsult___state____admin_state.authorized_rx_state_?(children?.at?.(0)):(children?.at?.(1)))
    )
});

export const Center_flex_08e3cc371f521fc6f933ce7e6b3bbfe9_fb35b5b8 = memo(({children}) => {
    const { rawColorMode } = useContext(ColorModeContext)



    return(
        jsx(RadixThemesFlex,{css:({ ["display"] : "flex", ["alignItems"] : "center", ["justifyContent"] : "center", ["width"] : "100%", ["minHeight"] : "100vh", ["background"] : ((rawColorMode?.valueOf?.() === "light"?.valueOf?.()) ? "radial-gradient(circle at top right, #f8fafc, #f1f5f9, #e2e8f0)" : "radial-gradient(circle at top right, #0a192f, #001f3f, #001529)") })},children)
    )
});
