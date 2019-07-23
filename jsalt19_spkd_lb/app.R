#
# A. Cristia for JSALT 2019
# alecristia@gmail.Com

### TODO
# add talker detection
# incorporate name+description using accompanying txt file

# i did the following to get the file lists
 # grep "Mix" /export/fs01/jsalt19/output_rttms/pipeline/v1/lda120_plda_voxceleb/jsalt19_spkdiar_ami_eval_Mix-Headset/plda_scores_tbest/result.pyannote-der | grep -v "arn" | cut -f 1 -d " " > ami_test.txt
 # grep "jsalt" /export/fs01/jsalt19/output_rttms/pipeline/v1/lda120_plda_voxceleb/jsalt19_spkdet_sri_eval_test/plda_scores_tbest/result.pyannote-der | grep -v "arn" | cut -f 1 -d " " > sri_test.txt
 # grep "_" /export/fs01/jsalt19/output_rttms/pipeline/v1/lda120_plda_voxceleb/jsalt19_spkdet_babytrain_eval_test/plda_scores_tbest/result.pyannote-der  | grep -v "arn" | cut -f 1 -d " " > babytrain_test.txt
 # grep "_U01" /export/fs01/jsalt19/output_rttms/pipeline/v1/lda120_plda_voxceleb/jsalt19_spkdiar_chime5_eval_U01/plda_scores_tbest/result.pyannote-der  | grep -v "arn" | cut -f 1 -d " " > chime5_test.txt



library(shiny)
library(RCurl)



# Define UI for application that draws a histogram
ui <- fluidPage(
   
   # Application title
   titlePanel("JSALT 2019 spk det leaderboard"),
   
   # Sidebar with a slider input for number of bins 
   sidebarLayout(
      sidebarPanel(
        selectInput(
          "corpus",
          "Corpus",
          c("BabyTrain" = "babytrain",
            "AMI" = "ami",
            "CHiME" = "chime5",
            "SRI" = "sri"
          ) 
        ),
        selectInput(
          "task",
          "task",
          c("Diarization" = "diar",
            "VAD" = "det"
          )
        ),
        checkboxInput("noGT", "Remove systems based on ground truth VAD",FALSE)
      ),
      
      # Show a plot of the generated distribution
      mainPanel(
         plotOutput("rank"),
         tabPanel("Data",DT::dataTableOutput("mytable"))
      )
   )
)

# Define server logic required to draw a histogram
server <- function(input, output) {

  myurl <- getURL("https://raw.githubusercontent.com/jsalt-coml/corstatana/master/demon/allres.txt")
  allres <- read.csv(text = myurl)
  allres$res=as.character(allres$res)
  for(thisc in levels(allres$corpus)) allres$res=gsub(thisc,"",allres$res)
  allres$res=gsub("_clean.*","",allres$res)

   output$rank <- renderPlot({
     # generate bins based on input$bins from ui.R
     x    <- allres[allres$corpus == input$corpus & allres$task== input$task, ] 
     if(input$noGT) x <- x[grep("gt",x$res,invert=T), ] 
     means=aggregate(x$main,by=list(x$res),mean, na.rm=T)
     colnames(means)=c("res","main")
     means=means[order(means$main),]
     
     mylabs=means$res
 #    mylabs=gsub("_","\n",mylabs)
#     mylabs=gsub("voxceleb\n","v",mylabs)
     
     # draw barplot ordering contributions by best to worst
     par(mar=c(8, 4, 2, 2.5))
     barplot(means$main, beside=T,  main=paste(input$task,"by system in",input$corpus), ylab=ifelse(input$task=="det","Det Err R","Diar Err R"),
             xaxt="n",xlab="",ylim=c(0,100))
     end_point = 0.8 + length(means$main)*1.2 -1 #this is the line which does the trick (together with barplot "space = 1" parameter)
     text(seq(0.8,end_point,by=1.2), par("usr")[3]-0.25, 
          srt = 45, adj= 1, xpd = TRUE, 
          labels = mylabs)
   })
   
   output$mytable = DT::renderDataTable({
     x    <- allres[allres$corpus == input$corpus & allres$task== input$task, ] 
     if(input$noGT) x <- x[grep("GT",x$res,invert=T), ] 
     means=aggregate(x$main,by=list(x$res),mean, na.rm=T)
     colnames(means)=c("res","main")
     means=means[order(means$main),]
     means
     
   },rownames = FALSE)
}

# Run the application 
shinyApp(ui = ui, server = server)

