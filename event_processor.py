import sys, platform, wx
import winsound
import globalVars
import lc_manager
import menuItemsStore

def is64Bit():
    return sys.maxsize > 2 ** 32

#使用環境に応じて適切なdllをロード
if is64Bit():
    from pybass64 import pybass
    from pybass64 import bass_fx
else:
    from pybass import pybass
    from pybass import bass_fx


class eventProcessor():
    def __init__(self):
        self.stopFlag = 0
        self.repeatLoopFlag = 0 #リピート=1, ループ=2


    def freeBass(self):
        # bass.dllをフリー
        pybass.BASS_Free()

    def refreshView(self):
        # ボタン表示更新
        if self.stopFlag ==1 or globalVars.play.handle == 0:
            globalVars.app.hMainView.playPauseBtn.SetLabel("再生")
        elif globalVars.play.getChannelState() == pybass.BASS_ACTIVE_PLAYING:
            globalVars.app.hMainView.playPauseBtn.SetLabel("一時停止")
        else:
            globalVars.app.hMainView.playPauseBtn.SetLabel("再生")

        #トラックバー更新
        max = globalVars.play.getChannelLength()
        if max != False and globalVars.play.getChannelState() != pybass.BASS_ACTIVE_STOPPED:
            globalVars.app.hMainView.trackBar.SetMax(max)
        else:
            globalVars.app.hMainView.trackBar.SetMax(0)
        val = globalVars.play.getChannelPosition()
        if val != False and globalVars.play.getChannelState() != pybass.BASS_ACTIVE_STOPPED:
            globalVars.app.hMainView.trackBar.SetValue(val)
        else:
            globalVars.app.hMainView.trackBar.SetValue(0)

        # リスト幅更新
        globalVars.app.hMainView.playlistView.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        globalVars.app.hMainView.queueView.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)


    def fileChange(self):
        # ストリームがないか停止状態であればファイルを再生
        if globalVars.play.handle == 0 or globalVars.play.getChannelState() == pybass.BASS_ACTIVE_STOPPED:
            if self.repeatLoopFlag == 1: #リピート
                globalVars.play.inputFile(globalVars.play.fileName)
            else: #それ以外（nextFileがループ処理）
                self.nextFile()

    def previousFile(self):
        p = False
        if self.stopFlag == 1:
            return None
        # プレイリスト再生中であれば
        get = globalVars.playlist.getFile()
        if get == globalVars.play.fileName:
            # プレイリストの1曲前を再生
            get = globalVars.playlist.getPrevious()
            if get != None:
                p = globalVars.play.inputFile(get)
            elif self.repeatLoopFlag == 2: #ループ指定の時は末尾へ
                get = globalVars.playlist.getFile(-1, True)
                if get != None:
                    p = globalVars.play.inputFile(get)
        elif get != None:
            # キューなどからの復帰
            p = globalVars.play.inputFile(get)
        # 停止中フラグの解除
        if p: self.stopFlag = 0

    def playButtonControl(self):
        # 再生中は一時停止を実行
        if globalVars.play.getChannelState() == pybass.BASS_ACTIVE_PLAYING:
            globalVars.play.pauseChannel()
        # 停止中であればファイルを再生
        elif self.stopFlag == 1:
            self.stopFlag = 0
            self.nextFile()
        else:
            globalVars.play.channelPlay()

    def nextFile(self):
        p = False
        # ユーザ操作による停止ではないか
        if self.stopFlag == 1:
            return None
        # キューを確認
        get = globalVars.queue.getNext()
        if get == None:
            # キューが空の時はプレイリストを確認
            get = globalVars.playlist.getNext()
            if get != None:
                p = globalVars.play.inputFile(get)
            elif self.repeatLoopFlag == 2: #ﾙｰﾌﾟであれば先頭へ
                get = globalVars.playlist.getFile(0,True)
                if get != None:
                    p = globalVars.play.inputFile(get)
            else: # 再生するものがなければ停止とする
                self.stopFlag = 1
        else:
            p = globalVars.play.inputFile(get)
        if p: self.stopFlag = 0

    def stop(self):
        self.stopFlag = 1
        globalVars.play.channelFree()
        globalVars.playlist.positionReset()

    #リピートﾙｰﾌﾟフラグを切り替え(モード=順次)
    def repeatLoopCtrl(self, mode=-1): #0=なし, 1=リピート, 2=ループ
        if mode == -1:
            if self.repeatLoopFlag < 2:
                self.repeatLoopFlag+=1
            else:
                self.repeatLoopFlag=0
        elif mode>=0 and mode<=2:
            self.repeatLoopFlag = mode
        if self.repeatLoopFlag == 0:
            globalVars.app.hMainView.repeatLoopBtn.SetLabel("ﾘﾋﾟｰﾄ / ﾙｰﾌﾟ")
            globalVars.app.hMainView.menu.hRepeatLoopInOperationMenu.Check(menuItemsStore.getRef("REPEAT_LOOP_NONE"), True)
        elif self.repeatLoopFlag == 1:
            globalVars.app.hMainView.repeatLoopBtn.SetLabel("只今: リピート")
            globalVars.app.hMainView.menu.hRepeatLoopInOperationMenu.Check(menuItemsStore.getRef("RL_REPEAT"), True)
        elif self.repeatLoopFlag == 2:
            globalVars.app.hMainView.repeatLoopBtn.SetLabel("只今: ループ")
            globalVars.app.hMainView.menu.hRepeatLoopInOperationMenu.Check(menuItemsStore.getRef("RL_LOOP"), True)

    def trackBarCtrl(self, bar):
        val = bar.GetValue()
        globalVars.play.setChannelPosition(val)
    
    # リストビューでアクティベートされたアイテムの処理
    def listSelection(self, evt):
        evtObj = evt.GetEventObject()
        if evtObj == globalVars.app.hMainView.playlistView:
            lst = globalVars.playlist
        elif evtObj == globalVars.app.hMainView.queueView:
            lst = globalVars.queue
        # 単一選択時アクティベートされた曲を再生
        iLst = lc_manager.getListCtrlSelections(evtObj)
        if len(iLst) == 1:
            index = evt.GetIndex()
            p = globalVars.play.inputFile(lst.getFile(index, True))
            if p: # 再生に成功
                self.stopFlag = 0
            else: # 再生に失敗（エラー処理）
                self.stopFlag = 1
            if lst == globalVars.queue:
                lst.deleteFile(index)

    def listViewKeyEvent(self, evt):
        evtObj = evt.GetEventObject()
        # 発生元とpythonリストの対応付け
        if evtObj == globalVars.app.hMainView.playlistView:
            lst = globalVars.playlist
        elif evtObj == globalVars.app.hMainView.queueView:
            lst = globalVars.queue
        kc = evt.GetKeyCode()
        # deleteで削除
        if kc == wx.WXK_DELETE:
            index = lc_manager.getListCtrlSelections(evtObj)
            cnt = 0
            for i in index:
                i = i-cnt
                lst.deleteFile(i)
                cnt += 1
