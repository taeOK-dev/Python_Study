using NetworkCommon;
using System;
using System.Collections.Generic;
using System.Linq;
using UniRx;

namespace AutoPlay
{
    public class QuestAuto
    {
        private GameMainPlayer mainPlayer => PlayerManager.instance.GetMainPlayer();

        private readonly ReactiveProperty<ObjectState> states = new ReactiveProperty<ObjectState>();
        private readonly CompositeDisposable disposable = new CompositeDisposable();

        public bool AutoMode = false;
        public Data_Quest_Scroll? selectedScroll = null;

        private Quest.Info AutoQuest => QuestManager.instance.AutoQuest;

        public QuestAuto()
        {
            states.Subscribe(Subscribe);
            Reset();
        }

        /// <summary>
        /// 포즈
        /// </summary>
        public void Pause()
        {
            //states.Value = ObjectState.Off;
            //AutoMode = false;
            QuestManager.instance.TestMode = false;
            QuestManager.instance.CancelAutoQuest();
            QuestManager.instance.RefreshAutoPlay?.Invoke();
        }

        /// <summary>
        /// 스톱
        /// </summary>
        public void Reset()
        {
            bSocial = false;
            states.Value = ObjectState.Off;
            AutoMode = false;
            QuestManager.instance.TestMode = false;
            QuestManager.instance.CancelAutoQuest();
            QuestManager.instance.RefreshAutoPlay?.Invoke();
        }

        /// <summary>
        /// 스타트
        /// </summary>
        public void Set()
        {
            QuestManager.instance.CancelAutoQuest();
            AutoMode = true;
            states.Value = ObjectState.On;
        }

        private void Subscribe(ObjectState state)
        {
            disposable.Clear();
            if (state != ObjectState.On) return;

            int iTime = ConstantDataTableManager.Instance.GetValueInt(Enum_DataConstant.QUEST_AUTOSYSTEM_ACCEPT_TIME);

            Observable
                .Timer(TimeSpan.FromSeconds(0), TimeSpan.FromSeconds(iTime))
                .Where(_ =>
                {
                    if (AutoMode == false) return false;
                    if (CheckGameState() == false) return false;
                    if (AutoQuest == null) return true;
                    else
                    {
                        if(Util.IsStopMove() && AutoPlayer.Instance.Move.State.Value == MoveState.Off)
                        {
                            QuestManager.instance.CancelAutoQuest();
                            return true;
                        }

                        return false;
                    }
                })
                .Subscribe(_ => { CheckQuestProgress(); }).AddTo(disposable);
        }

        private bool CheckGameState()
        {
            if (ReferenceEquals(mainPlayer, null)) return false;
            if (UIGlobalHandler.instance.IsLockScreen()) return false;
            if (UIGlobalHandler.instance.LoadProcessInfo.IsActiveLoad) return false;

            //if (UIManager.instance.ActiveScene != SCENE_VALUE.eSCENE_INGAME) return false;
            //if (UISceneManager.instance.activeDlg != SCENEDIALOG.None) return false;
            if (UIManager.instance.IsCurrentDialog(SCENEDIALOG.QuestTalkDialog)) return false;
            if (UIManager.instance.IsCurrentDialog(SCENEDIALOG.NPCTalkDialog)) return false;
            if (Option.OptionDatabase.instance.OptionData.questAutoOption.useRewardAutoSelect.Value == false)
            {
                //1.리워드창의 띄워져 있으면
                //2.리워드아이템정보를 확인하면 현재 다이얼로그가 퀘스트대화창이 아니게 됨...
                var dialog = UIManager.instance.GetDialog(SCENEDIALOG.QuestTalkDialog) as QuestTalkDialog;
                if (dialog.rewardInfo.SelectedBox == false) return false;
            }
            if (DirectManager.instance.isScenePlaying) return false;
            if (DirectManager.instance.isDirectPlaying) return false;
            if (GameUser.Instance.GatherData.IsGatherState) return false;

            return true;
        }

        /// <summary>
        /// 중복 코드 !!!
        /// </summary>
        public bool CheckAutoQuest()
        {
            if (CheckGameState() == false) return false;
            if (!ReferenceEquals(null, AutoQuest)) return false;

            //실행가능한 퀘스트타입 추가
            List<eQuestType> typelist = new List<eQuestType>();
            if (Option.OptionDatabase.instance.OptionData.questAutoOption.useMainQuest.Value)
                typelist.Add(eQuestType.Main);
            if (Option.OptionDatabase.instance.OptionData.questAutoOption.useSubQuest.Value)
                typelist.Add(eQuestType.Sub);
            if (Option.OptionDatabase.instance.OptionData.questAutoOption.useEpisodeQuest.Value)
                typelist.Add(eQuestType.Episode);
            if (Option.OptionDatabase.instance.OptionData.questAutoOption.useScrollQuest.Value)
                typelist.Add(eQuestType.Scroll);
            if (typelist.IsNullOrEmpty())
            {
                return false;
            }

            List<Quest.Info> questList = QuestManager.instance.ProgressQuest;
            List<Quest.Info> sortList = QuestUtil.SortQuestType(questList, typelist);
            if (sortList.IsNullOrEmpty())
            {
                if(CheckScrollQuest() == false)
                {
                    return false;
                }
                else
                {
                    return true;
                }
            }

            Quest.Info info = null;
            foreach (var v in sortList)
            {
                if (GetQuest(v))
                {
                    info = v;
                    break;
                }
            }
            if (info == null)
            {
                if (CheckScrollQuest() == false)
                {
                    return false;
                }
            }

            return true;
        }
#if _MADDUCK
        public eQuestType lastType = eQuestType.None;

        public void CheckAutoProgress()
        {
            if (AutoMode == false) return;
            if (CheckGameState() == false) return;
            if (!ReferenceEquals(null, AutoQuest)) return;

            List<Quest.Info> questList = QuestManager.instance.ProgressQuest;
            List<Quest.Info> sortList = QuestUtil.SortQuestType(questList, lastType);
            if (sortList.IsNullOrEmpty())
            {
                sortList = QuestUtil.SortQuestType(questList);
                if (sortList.IsNullOrEmpty())
                {
                    if (CheckScrollQuest(true) == false)
                    {
                        NoQuest();
                    }
                    return;
                }
            }

            Quest.Info info = null;
            foreach (var v in sortList)
            {
                if (GetQuest(v))
                {
                    info = v;
                    break;
                }
            }
            if (info == null)
            {
                if (CheckScrollQuest(true) == false)
                {
                    NoQuest();
                }
                return;
            }

            QuestProgress(info);

            var hud = UIManager.instance.NowScene<InGameHUDScene>(SCENE_VALUE.eSCENE_INGAME);
            if (hud == null) return;
            hud.OnClick_PetSkill();

            void NoQuest()
            {
                //자동으로 진행할 수 있는 퀘스트가 없으면 자동 사냥.
                AutoPlayer.Instance.Button.SetAllTarget();
                //자동으로 진행할 수 있는 퀘스트가 없습니다
                var strMsg = UIUtil.UIString(STRINGTABLETYPE.eNoneString, 913);
                UIGlobalHandler.instance.ShowMessage(strMsg);
                UIGlobalHandler.instance.Show(CommonPopupType.MB_OK, strMsg);
                Reset();
            }
        }

        private void QuestProgress(Quest.Info info)
        {
            if(info.Type == eQuestType.Daily)
            {
                if (GameUser.Instance.CompareMapType(eMapType.QuestDungeon))
                {
                    QuestManager.instance.SetAutoQuest(info);
                }
                else
                {
                    if (info.State == Quest.State.OPEN)
                    {
                        SuperSocketServer.PacketSender.RequestDailyQuestOpen(true);
                    }
                    else if (info.State == Quest.State.ACCEPT)
                    {
                        SuperSocketServer.PacketSender.RequestDailyQuestEnter(true);
                        GameUser.Instance.DungeonData.SetDailyQuestID(info.ID);
                    }
                }
            }
            //첫 메인퀘스트는 예외
            else if (info.State == Quest.State.OPEN
                && info.Type != eQuestType.ChangeJob
                && info.Type != eQuestType.Main)
            {
                //수락
                QuestManager.instance.SendQuestAccept(info, null);
            }
            else if (info.State == Quest.State.COMPLETE)
            {
                if (info.Type == eQuestType.Scroll)
                {
                    //스크롤퀘스트 보상
                    QuestManager.instance.SendQuestReward(info, null);
                }
                else if (info.Type == eQuestType.Main)
                {
                    if (info.ProgressType != Quest.ProgressType.Talk
                        && info.ProgressType != Quest.ProgressType.Delivery)
                    {
                        QuestManager.instance.SendQuestReward(info, null);
                    }
                    else
                    {
                        QuestManager.instance.SetAutoQuest(info);
                    }
                }
                else
                {
                    QuestManager.instance.SetAutoQuest(info);
                }
            }
            else
            {
                QuestManager.instance.SetAutoQuest(info);
            }

            lastType = info.Type;
            ChekcAutoAtk(info);

            void ChekcAutoAtk(Quest.Info info)
            {
                switch (info.ProgressType)
                {
                    case Quest.ProgressType.Object_Dungeon:
                    case Quest.ProgressType.Dungeon_Talk:
                        {
                            if (GameUser.Instance.CompareMapType(
                                eMapType.QuestField, eMapType.QuestDungeon))
                            {
                                AutoPlayer.Instance.QuestAuto.Reset();
                                AutoPlayer.Instance.Button.SetAllTarget();
                            }
                        }
                        break;

                    default:
                        break;
                }
            }
        }

#else
        /// <summary>
        /// 던전퀘스트를 먼저 체크하고
        /// </summary>
        public void CheckQuestProgress()
        {
            if (AutoMode == false) return;
            if (CheckGameState() == false) return;
            if (!ReferenceEquals(null, AutoQuest)) return;

            List<Quest.Info> questList = QuestManager.instance.ProgressQuest;
            List<Quest.Info> sortList = QuestUtil.SortQuestType(questList, eQuestType.DungeonQuest);
            if (sortList.IsNullOrEmpty())
            {
                CheckAutoProgress();
                return;
            }

            Quest.Info info = sortList[0];
            if (info.State != Quest.State.COMPLETE)
                QuestProgress(info);
        }

        public void CheckAutoProgress()
        {
            if (AutoMode == false) return;
            if (CheckGameState() == false) return;
            if (!ReferenceEquals(null, AutoQuest)) return;

            //실행가능한 퀘스트타입 추가
            List<eQuestType> typelist = new List<eQuestType>();
            if (Option.OptionDatabase.instance.OptionData.questAutoOption.useMainQuest.Value)
                typelist.Add(eQuestType.Main);
            if (Option.OptionDatabase.instance.OptionData.questAutoOption.useSubQuest.Value)
                typelist.Add(eQuestType.Sub);
            if (Option.OptionDatabase.instance.OptionData.questAutoOption.useEpisodeQuest.Value)
                typelist.Add(eQuestType.Episode);
            if (Option.OptionDatabase.instance.OptionData.questAutoOption.useScrollQuest.Value)
                typelist.Add(eQuestType.Scroll);
            if (typelist.IsNullOrEmpty())
            {
                NoQuest();
                return;
            }

            List<Quest.Info> questList = QuestManager.instance.ProgressQuest;
            List<Quest.Info> sortList = QuestUtil.SortQuestType(questList, typelist);
            if (sortList.IsNullOrEmpty())
            {
                if (CheckScrollQuest(true) == false)
                {
                    NoQuest();
                }
                return;
            }

            Quest.Info info = null;
            foreach (var v in sortList)
            {
                if (GetQuest(v))
                {
                    info = v;
                    break;
                }
            }
            if (info == null)
            {
                if (CheckScrollQuest(true) == false)
                {
                    NoQuest();
                }
                return;
            }

            QuestProgress(info);

            void NoQuest()
            {
                //자동으로 진행할 수 있는 퀘스트가 없으면 자동 사냥.
                AutoPlayer.Instance.Button.SetAllTarget();
                //자동으로 진행할 수 있는 퀘스트가 없습니다
                var strMsg = UIUtil.UIString(STRINGTABLETYPE.eNoneString, 913);
                UIGlobalHandler.instance.ShowMessage(strMsg);
                UIGlobalHandler.instance.Show(CommonPopupType.MB_OK, strMsg);
                Reset();
            }
        }
#endif

        private void QuestProgress(Quest.Info info)
        {
            if (AutoMode == false) return;

            //첫 메인퀘스트는 예외
            if (info.State == Quest.State.OPEN && info.Type != eQuestType.Main)
            {
                //수락
                QuestManager.instance.SendQuestAccept(info, null);
            }
            else if (info.State == Quest.State.COMPLETE && info.Type == eQuestType.Scroll)
            {
                //스크롤퀘스트 보상
                QuestManager.instance.SendQuestReward(info, null);
            }
            else
            {
                QuestManager.instance.SetAutoQuest(info);
            }

            //lastType = info.Type;
            ChekcAutoAtk(info);

            void ChekcAutoAtk(Quest.Info info)
            {
                switch (info.ProgressType)
                {
                    case Quest.ProgressType.Object_Dungeon:
                    case Quest.ProgressType.Dungeon_Talk:
                        {
                            if (GameUser.Instance.CompareMapType(
                                eMapType.QuestField, eMapType.QuestDungeon))
                            {
                                AutoPlayer.Instance.QuestAuto.Pause();
                                AutoPlayer.Instance.Button.SetAllTarget();
                            }
                        }
                        break;

                    default:
                        break;
                }
            }
        }

        //스크롤퀘스트
        bool CheckScrollQuest(bool bPlay = false)
        {
            if (Option.OptionDatabase.instance.OptionData.questAutoOption.useScrollQuest.Value)
            {
                if (selectedScroll.HasValue)
                {
                    //하루 사용 횟수 체크
                    int nCount = Quest.Constant.MAX_SCROLL_COUNT - QuestManager.instance.ScrollQuestCount;
                    if (nCount <= 0) return false;

                    var ownerCharacter = GameUser.Instance.SelectedGameCharacter;
                    var item = ownerCharacter.FindItemByItemId(
                        NetworkCommon.eInvenType.Etc_Use, selectedScroll.Value.ItemID) as EtcItem;

                    if (item == null) return false;

                    if (bPlay) SuperSocketServer.ServerManager.instance.RequestMainItemUse(item.UID, (short)eInvenType.Etc_Use, 1);
                    return true;
                }
            }
            return false;
        }

        bool bSocial = false;
        /// <summary>
        /// 실행 가능한 수행타입인지 여부 판단
        /// </summary>
        private bool GetQuest(Quest.Info info)
        {
            var character = GameUser.Instance.SelectedGameCharacter;

            //OpenLevel 체크
            switch (info.Type)
            {
                case eQuestType.Main:
                    {
                        var table = QuestTableManager.Instance.GetMainQuestTable(info.ID);
                        if (table.OpenLevel > character.CharacterLevel) return false;
                        break;
                    }
                case eQuestType.Sub:
                    {
                        var table = QuestTableManager.Instance.GetSubQuestTable(info.ID);
                        if (table.OpenLevel > character.CharacterLevel) return false;
                        break;
                    }
                case eQuestType.Episode:
                    {
                        var table = QuestTableManager.Instance.GetEpisodeQuestTable(info.ID);
                        if (table.OpenLevel > character.CharacterLevel) return false;
                        break;
                    }
                case eQuestType.Scroll:
                    {
                        return true;
                    }
            }

            switch (info.ProgressType)
            {
                case Quest.ProgressType.Talk:
                case Quest.ProgressType.Delivery:
                case Quest.ProgressType.Object_Item:
                case Quest.ProgressType.Object_Count:
                case Quest.ProgressType.Hunt_Item:
                case Quest.ProgressType.Hunt_Count:
                case Quest.ProgressType.Hunt_Level:
                case Quest.ProgressType.Hunt_Area:
                case Quest.ProgressType.Move_Area:
                case Quest.ProgressType.Inquiry_Area:
                case Quest.ProgressType.Branch:
                case Quest.ProgressType.Action_Gather:
                    return true;
                case Quest.ProgressType.Quiz:
                    return false;
                case Quest.ProgressType.Action_Social:
                case Quest.ProgressType.Action_UseItem:
                case Quest.ProgressType.Action_LvUp:
                case Quest.ProgressType.Dungeon_Enter:
                case Quest.ProgressType.Dungeon_Clear:
                case Quest.ProgressType.Action_Level:
                case Quest.ProgressType.Action_JobLevel:
                {
                    //자동으로 진행할 수 있는 퀘스트가 없습니다
                    var strMsg = UIUtil.UIString(STRINGTABLETYPE.eNoneString, 913);
                    UIGlobalHandler.instance.ShowMessage(strMsg);
                    UIGlobalHandler.instance.Show(CommonPopupType.MB_OK, strMsg);
                    Reset();
                    return false;
                }
                case Quest.ProgressType.Object_Dungeon:
                case Quest.ProgressType.NPC_Escort:
                case Quest.ProgressType.NPC_Subjugation:
                case Quest.ProgressType.Dungeon_Talk:
                {
                    if (bSocial) return false;
                    bSocial = true;

                    //퀘스트 던전에서 진행하는 퀘스트는 자동으로 진행할 수 없습니다.
                    var strMsg = UIUtil.UIString(STRINGTABLETYPE.eUI, 13542);
                    UIGlobalHandler.instance.Show(CommonPopupType.MB_OK, strMsg);
                    return false;
                }
            }

            //모두 가능
            return true;
        }

        /// <summary>
        /// 던전입장시 자동퀘스트 취소
        /// </summary>
        public void CheckAvailableMap()
        {
            if (AutoPlayer.Instance.QuestAuto.AutoMode)
            {
                if (GameUser.Instance.IsDungeonMapType
                    || GameUser.Instance.IsBattleMapType)
                {
                    AutoPlayer.Instance.QuestAuto.Reset();
                }
                else if (GameUser.Instance.CompareMapType(
                        NetworkCommon.eMapType.QuestField,
                        NetworkCommon.eMapType.QuestDungeon))
                {
                    AutoPlayer.Instance.QuestAuto.Reset();
                }
            }
        }
    }
}